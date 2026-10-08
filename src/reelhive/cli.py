"""ReelHive command-line interface.

* ``run``    — brief in, video out.
* ``doctor`` — check every dependency and API key.
"""

from __future__ import annotations

from pathlib import Path

import typer
import yaml
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from reelhive import __version__
from reelhive.config import load_config
from reelhive.core.events import Event
from reelhive.schemas.brief import Brief

app = typer.Typer(add_completion=False, help="Turn a short brief into a narrated, scored video.")
console = Console()


def _version_callback(value: bool):
    if value:
        console.print(f"ReelHive {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    _version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True, help="Show version and exit."
    ),
):
    """ReelHive — brief in, video out."""


def _printer(verbose: bool):
    last_progress = {"value": -1.0}

    def on_event(e: Event) -> None:
        d = e.data
        if e.type == "node.started":
            console.print(f"[bold]▸ {d['node']}[/bold]")
        elif e.type == "node.task":
            if "progress" in d:
                step = int(d["progress"] * 10)
                if step == last_progress["value"]:
                    return
                last_progress["value"] = step
                console.print(f"  [dim]{d['node']} · {d['task']} {d['progress']:.0%}[/dim]")
            else:
                console.print(f"  [dim]{d['node']} · {d['task']}[/dim]")
        elif e.type == "node.finished":
            if d["status"] == "completed":
                tokens = f" · {d['tokens']:,} tokens" if d.get("tokens") else ""
                console.print(f"[green]✓ {d['node']}[/green] [dim]{d['seconds']}s{tokens}[/dim]")
            else:
                console.print(f"[red]✗ {d['node']}[/red] {d.get('error', '')}")
        elif e.type == "node.skipped":
            console.print(f"[dim]– {d['node']} skipped[/dim]")
        elif e.type == "gate.result":
            mark = "[green]✓[/green]" if d["passed"] else "[red]✗[/red]"
            console.print(f"  {mark} {d['check']}: {d['value']} [dim]({d['threshold']})[/dim]")
        elif e.type == "critic.verdict":
            scores = ", ".join(f"{k} {v}" for k, v in d["scores"].items())
            console.print(f"  critic: {'pass' if d['passed'] else 'fail'} [dim]({scores})[/dim]")
            for reason in d["reasons"]:
                console.print(f"    [yellow]• {reason}[/yellow]")
        elif e.type == "fix.diff":
            console.print(f"  [yellow]fix changed {len(d['changes'])} scenes[/yellow]")
        elif e.type == "agent.text" and verbose:
            console.print(d["text"], end="", markup=False, highlight=False)

    return on_event


@app.command()
def run(
    brief_file: Path = typer.Argument(..., exists=True, dir_okay=False, help="Brief YAML file."),
    config_file: Path = typer.Option(None, "--config", exists=True, dir_okay=False, help="config.yaml path."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Stream agent output."),
):
    """Make a video from a brief."""
    from reelhive.core.service import Service
    from reelhive.providers.factory import ProviderError

    try:
        brief = Brief.model_validate(yaml.safe_load(brief_file.read_text()))
        config = load_config(config_file)
    except ValidationError as e:
        console.print(f"[red]Invalid {brief_file if 'Brief' in e.title else 'config'}:[/red]")
        for err in e.errors():
            console.print(f"  • {'.'.join(str(p) for p in err['loc']) or 'root'}: {err['msg']}")
        raise typer.Exit(2) from e

    service = Service(config)
    try:
        result = service.run(brief, on_event=_printer(verbose))
    except ProviderError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(2) from e
    except Exception as e:
        console.print(f"[red]Run failed:[/red] {e}")
        raise typer.Exit(1) from e

    if result.status == "done":
        console.print(f"\n[bold green]Video ready:[/bold green] {result.video}")
    elif result.status == "awaiting_script":
        console.print(f"\n[bold]Script ready for review:[/bold] {result.run_dir / 'script.json'}")
        console.print(f"Edit that file if needed, then run: reelhive approve {result.run_dir}")
    else:
        console.print("\n[bold red]Stopped before rendering.[/bold red] The spec still fails these checks:")
        for line in result.report:
            console.print(f"  • {line}")
        console.print(f"[dim]Run folder: {result.run_dir}[/dim]")
        raise typer.Exit(1)


@app.command()
def doctor(config_file: Path = typer.Option(None, "--config", exists=True)):
    """Check every dependency and API key."""
    from reelhive.doctor import run_checks

    results = run_checks(load_config(config_file))
    table = Table(title="ReelHive doctor")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")
    for r in results:
        status = "[green]ok[/green]" if r.ok else ("[red]missing[/red]" if r.required else "[yellow]warn[/yellow]")
        table.add_row(r.name, status, r.detail)
    console.print(table)
    if any(r.required and not r.ok for r in results):
        raise typer.Exit(1)


@app.command()
def approve(
    run_dir: Path = typer.Argument(..., exists=True, file_okay=False),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """Approve the saved script.json and continue a medium run."""
    from reelhive.config import Config
    from reelhive.core.service import Service

    try:
        config = Config.model_validate_json((run_dir / "config.json").read_text())
        result = Service(config).approve(run_dir, on_event=_printer(verbose))
    except Exception as e:
        console.print(f"[red]Approval failed:[/red] {e}")
        raise typer.Exit(1) from e
    if result.status != "done":
        console.print(f"[red]Stopped:[/red] {'; '.join(result.report)}")
        raise typer.Exit(1)
    console.print(f"[green]Video ready:[/green] {result.video}")


@app.command()
def login(url: str, output: Path = typer.Option(Path("auth.json"), "--output")):
    """Sign in manually and save a private browser session for screenshots."""
    from reelhive.visuals.login import login as save_login

    save_login(url, output)
    console.print(f"Session saved to {output}")


@app.command()
def capture(
    brief_file: Path = typer.Argument(..., exists=True, dir_okay=False),
    output: Path = typer.Option(Path("runs/capture"), "--output"),
):
    """Preview masked screenshots before making a video."""
    from reelhive.visuals.capture import capture as screenshot
    from reelhive.visuals.capture import discover

    brief = Brief.model_validate(yaml.safe_load(brief_file.read_text()))
    options = brief.visuals.screenshots
    if options is None:
        raise typer.BadParameter("brief has no screenshot source")
    output.mkdir(parents=True, exist_ok=True)
    for i, page in enumerate(discover(options, brief.format), 1):
        path = output / f"page_{i:02d}.png"
        screenshot(options, brief.format, page["route"], path)
        console.print(f"{path}: {page['title']}")


@app.command()
def models(
    provider: str = typer.Option("copilot", "--provider"),
    config_file: Path = typer.Option(None, "--config", exists=True),
):
    """List Copilot's available models, or configured models for another provider."""
    import asyncio

    from reelhive.providers.copilot.node import list_models

    try:
        if provider == "copilot":
            names = asyncio.run(list_models())
        else:
            config = load_config(config_file)
            if provider not in config.models:
                raise ValueError(f"no models configured for {provider}")
            names = list(config.models[provider].model_dump().values())
        for name in names:
            console.print(name)
    except Exception as e:
        console.print(f"[red]Cannot list models:[/red] {e}")
        raise typer.Exit(1) from e
