# `src`

**Overview.** The Python source, in the standard `src/` layout so tests always run against the installed package rather than loose files. There is one package: [`reelhive`](reelhive), which has its own README and one per subpackage.

Install it for development with `make setup` (or `uv sync --extra dev`), which installs it in editable mode. Cloning is the install method: the Node renderer and the UI sit next to it in the repo.
