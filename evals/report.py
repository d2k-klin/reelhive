"""One comparison report per eval run: a table per metric per provider, as Markdown and HTML."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from evals.run import METRICS


def _fmt(key: str, value: Any) -> str:
    if value is None:
        return "–"
    rate = key in (
        "success",
        "schema_first_try",
        "duration_ok",
        "feature_coverage",
        "pace_ok",
        "text_fit",
        "visual_coverage",
    )
    return f"{value:.0%}" if rate else f"{value:,.2f}".rstrip("0").rstrip(".")


def rows(report: dict[str, Any]) -> tuple[list[str], list[list[str]]]:
    stats = report["providers"]
    providers = list(stats)
    body = [[label, *(_fmt(key, report["providers"][p].get(key)) for p in providers)] for key, label, _ in METRICS]
    nodes = sorted({n for p in providers for n in report["providers"][p]["node_seconds"]})
    for node in nodes:
        body.append(
            [
                f"`{node}` seconds / tokens (mean)",
                *(
                    f"{stats[p]['node_seconds'].get(node, 0):g} / {stats[p]['node_tokens'].get(node, 0):g}"
                    for p in providers
                ),
            ]
        )
    return ["Metric", *providers], body


def to_markdown(report: dict[str, Any]) -> str:
    head, body = rows(report)
    lines = [
        f"# ReelHive eval: `{report['set']}` set",
        "",
        f"{len(report['briefs'])} briefs · {report['created']} · judge {'on' if report['judge'] else 'off'}",
        "",
        "| " + " | ".join(head) + " |",
        "|" + " --- |" * len(head),
        *("| " + " | ".join(r) + " |" for r in body),
        "",
        "## Runs that did not reach render",
        "",
    ]
    failed = [r for r in report["records"] if r["outcome"] != "done"]
    lines += [f"- {r['provider']} · {r['brief']}: {r['outcome']} {r.get('error', '')}".rstrip() for r in failed]
    lines += [] if failed else ["None."]
    return "\n".join(lines) + "\n"


def to_html(report: dict[str, Any]) -> str:
    head, body = rows(report)
    e = html.escape
    table = (
        "<tr>"
        + "".join(f"<th>{e(h)}</th>" for h in head)
        + "</tr>"
        + "".join("<tr>" + "".join(f"<td>{e(c)}</td>" for c in r) + "</tr>" for r in body)
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>ReelHive eval</title>
<style>body{{font:15px system-ui;margin:32px;color:#1c1917}}table{{border-collapse:collapse}}
td,th{{border:1px solid #d6d3d1;padding:6px 12px;text-align:right}}td:first-child,th:first-child{{text-align:left}}
th{{background:#f5f5f4}}</style></head><body><h1>ReelHive eval: {e(report["set"])}</h1>
<p>{len(report["briefs"])} briefs · {e(report["created"])}</p><table>{table}</table></body></html>
"""


def write_reports(report: dict[str, Any], out: Path) -> None:
    (out / "report.md").write_text(to_markdown(report))
    (out / "report.html").write_text(to_html(report))
