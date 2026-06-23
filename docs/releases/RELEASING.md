# Releasing `ccw-mcp`

This runbook documents the canonical public release flow for this repository.

## 1) Preflight

- Ensure you are on `main` with a clean working tree.
- Ensure the project virtualenv exists and is active, or use `.venv/bin/python`.
- Confirm you can run the full test suite:

```bash
.venv/bin/python -m unittest
```

## 2) Choose the new version

Use semantic versioning:

- patch: bug fix or behavior refinement (`0.1.2` -> `0.1.3`)
- minor: backward-compatible feature additions
- major: breaking changes

## 3) Update versioned files

Bump the same version in all release metadata:

- `pyproject.toml` -> `[project].version`
- `src/ccw/__init__.py` -> `__version__`
- `apm.yml` -> `version`

If the release changes user-visible behavior, also update:

- `README.md` (install/upgrade/use changes)
- `docs/releases/<version>.md` (release notes)

## 4) Validate before commit

```bash
.venv/bin/python -m unittest
```

Optional but recommended:

```bash
git diff --stat
```

## 5) Commit release changes

Use a release-style message:

```bash
git add pyproject.toml src/ccw/__init__.py apm.yml README.md docs/releases/
git commit -m "Release ccw-mcp X.Y.Z"
```

## 6) Build distributions

```bash
.venv/bin/python -m pip install -U build twine
rm -rf dist build
.venv/bin/python -m build
```

Expected artifacts:

- `dist/ccw_mcp-X.Y.Z-py3-none-any.whl`
- `dist/ccw_mcp-X.Y.Z.tar.gz`

## 7) Publish to PyPI

Preferred path: use the helper script that loads local `.env` secrets and maps
common token variable names safely:

```bash
scripts/release-pypi.sh
```

The helper checks:

- `.venv/bin/python` exists
- `dist/` contains built artifacts
- one of the supported token variables is set

It reads local `.env` if present and maps token variables into Twine auth.

Load credentials manually only if needed. The recommended variables are:

- `TWINE_USERNAME=__token__`
- `TWINE_PASSWORD=<pypi-token>`

If your `.env` uses a different token variable (for example `PYPI_TOKEN`), map
it into `TWINE_PASSWORD` before upload.

```bash
set -a && source .env && set +a
export TWINE_USERNAME=__token__
export TWINE_PASSWORD="${TWINE_PASSWORD:-${PYPI_API_TOKEN:-${PYPI_TOKEN:-${PYPI_TOKEN_PROD:-}}}}"
.venv/bin/python -m twine upload dist/*
```

## 8) Post-publish checks

- Verify the new release page exists on PyPI:
  - `https://pypi.org/project/ccw-mcp/X.Y.Z/`
- Verify installation from a clean environment:

```bash
python -m venv /tmp/ccw-release-check
/tmp/ccw-release-check/bin/python -m pip install -U ccw-mcp==X.Y.Z
/tmp/ccw-release-check/bin/python -c "import ccw; print(ccw.__version__)"
```

## 9) Push commit and tag

```bash
git tag vX.Y.Z
git push origin main --tags
```

## 10) Client upgrade communication

Document upgrade commands for users in release notes:

- `pip install -U ccw-mcp`
- `pipx upgrade ccw-mcp`
- `uvx --refresh ccw-mcp==X.Y.Z --help`
- restart harness/editor process after upgrade

Without process restart, MCP clients may keep running an older server binary.
