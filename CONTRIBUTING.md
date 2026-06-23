# Contributing

## Before you start

- Use GitHub Issues for bug reports and feature requests.
- For large changes, open or reference an issue before you start coding.
- Keep pull requests small, focused, and easy to review.

## Local setup

CCW requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Validation

Run the full repo test suite before opening a pull request:

```bash
python -m unittest
```

## Documentation expectations

- Update `README.md` when public CLI behavior, install steps, or examples change.
- For packaged releases, follow `docs/releases/RELEASING.md` and add release notes
  under `docs/releases/`.
- Use `scripts/release-pypi.sh` for PyPI upload so local `.env` token handling
  stays consistent and secret-safe.
- Update the relevant page under `wiki/user/` and append one line to
  `wiki/user/log.md` when architecture, roadmap, slice, or workflow assumptions
  change.
- Keep `CONTEXT.md` aligned with durable product vocabulary.

## Pull requests

- Add or update tests for behavior changes.
- Do not commit generated or runtime state such as `.ccw/`, `.venv/`, `build/`,
  `dist/`, or `*.egg-info`.
- Call out user-visible behavior, validation, and documentation changes in the
  pull request description.

## License

By contributing to this repository, you agree that your contributions will be
licensed under the MIT License that covers this project.
