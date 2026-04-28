# Contributing to geoimagery

Thanks for taking the time to contribute! This document covers the dev workflow.

## Quick start

```bash
git clone https://github.com/hpa-code/geoimagery
cd geoimagery
python -m venv .venv && source .venv/bin/activate  # or use uv / rye / poetry
pip install -e ".[dev]"
pre-commit install
```

## Running checks

| Task | Command |
|---|---|
| Lint + format check | `ruff check . && ruff format --check .` |
| Auto-fix lint + format | `ruff check --fix . && ruff format .` |
| Type check | `mypy` |
| Unit tests (no GEE) | `pytest -m "not integration"` |
| Integration tests (requires GEE auth) | `pytest -m integration` |
| Coverage report | `pytest --cov` |

`pre-commit` will run the fast checks automatically on every commit.

## Conventions

- **Style.** All code is formatted by ruff. Run `ruff format .` before committing — pre-commit will catch you anyway.
- **Docstrings.** NumPy-style. Every public function has one.
- **Type hints.** Required on all public APIs. `mypy` is run in CI.
- **Tests.** Anything that hits Earth Engine should be marked `@pytest.mark.integration`. Pure-Python helpers should have plain unit tests.
- **Commit messages.** Imperative mood ("Add NAIP support" not "Added NAIP support"). Conventional Commits prefixes (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`) are encouraged but not enforced.
- **Public API stability.** Anything exported from `geoimagery/__init__.py` is public and follows SemVer. Internals (anything under a `_module` or starting with `_`) can change without notice.

## Reporting bugs

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.yml). Please include:

- Python version (`python --version`)
- `geoimagery` version (`python -c "import geoimagery; print(geoimagery.__version__)"`)
- Versions of `earthengine-api`, `geemap`, `geopandas`
- A minimal reproducible example
- The full traceback

## Proposing changes

1. Open an issue first for anything more than a small fix — it's easier to align on direction before code review.
2. Branch from `main`, work in your branch.
3. Add tests. New behaviour without a test will be asked for one.
4. Update `CHANGELOG.md` under the `## [Unreleased]` section.
5. Open a PR using the [PR template](.github/PULL_REQUEST_TEMPLATE.md).

## Releasing (maintainers only)

1. Bump the version in `src/geoimagery/__version__.py`.
2. Move the `## [Unreleased]` entries in `CHANGELOG.md` under a new dated heading.
3. Tag and push: `git tag v0.X.Y && git push --tags`.
4. The `release.yml` workflow builds and publishes to PyPI via [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) — no token handling required.

## Code of Conduct

This project follows the [Contributor Covenant 2.1](CODE_OF_CONDUCT.md). Be kind.
