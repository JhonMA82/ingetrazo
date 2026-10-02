# Development guide

## Setup

```bash
uv sync
uv run python main.py
```

`uv sync` creates `.venv/` from `pyproject.toml` + `uv.lock`; `uv run` uses it.
Those two files are the dependency source of truth.

Requires Python 3.12+.

## Running tests

```bash
uv run pytest -q -m "not slow"     # the fast suite (3,536 tests; what CI runs)
uv run pytest -q                   # everything (4,341), including the slow fuzz sweeps
```

Every pull request runs the fast suite. A fix or a feature comes with its
test — ideally one that fails without the change. A test that paints
needs a real OpenGL context: guard it with a skip when there is none, or the
CI runner (no GPU) fails it.

## Style

- PEP 8, 100-character soft limit.
- All code, comments and commit messages in English.
- UI strings localized via `i18n/`. Never hardcode user-facing text.

## Submitting changes

See [../CONTRIBUTING.md](../CONTRIBUTING.md).
