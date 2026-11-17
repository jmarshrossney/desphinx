# AGENTS.md

## Project overview

`desphinx` finds and fixes reStructuredText and Sphinx markup in Python docstrings and comments, for projects whose API reference is Markdown rendered by mkdocstrings. `README.md` explains why it is a standalone command with a pre-commit hook.

## Source layout

```
src/desphinx/
  checker.py       — the rules (`RULES`), `check` and `fix`; no dependencies
  cli.py           — argparse entry point, `desphinx`
  __main__.py      — `python -m desphinx`
tests/             — one test file per module, plus `test_readme.py`
docs/              — index.md (introduction, usage, example) and reference.md (rules, API)
docs/snippets/     — before.py; `just docs-example` writes after.py and output.txt beside it
.pre-commit-hooks.yaml — the hook other repositories install
```

## Conventions specific to this package

- The package has no runtime dependencies, so the hook installs quickly and `uvx` runs it without a project. Keep it that way: no typer, no griffe.
- Only docstrings and comments are examined, never runtime strings. A new rule declares which of the two it applies to.
- `fix` rewrites only markup with exactly one Markdown equivalent. Anything needing a judgement (a fence language, where to move a docstring) is reported, never rewritten.
- The rules table in `README.md` must list every rule in `RULES`, in order, with a matching fix column; `tests/test_readme.py` checks. `docs/reference.md` includes the same table through its snippet section markers, so it is written once.
- `ruff format` rewrites Python code blocks in Markdown, which mangles snippet lines, so `docs/index.md` is excluded from formatting. `tests/test_docs.py` fails on a malformed or dangling snippet line.
- The home page example is produced by running the CLI at docs build time: `just docs-example` runs `desphinx --fix` on a copy of `docs/snippets/before.py` and writes the fixed module and the terminal session beside it (gitignored), which `pymdownx.snippets` includes. `before.py` must trigger every rule (`tests/test_examples.py`). It contains reST on purpose, so it sits outside the paths the package checks itself on, and the local pre-commit hook excludes it.
- The package checks itself: `just lint` and the local pre-commit hook run it over `src` and `tests`. Test fixtures that contain reST markup must therefore be runtime strings, not docstrings or comments.

## Commands

All via `just`, prefixed with `uv run` unless the virtual environment is activated: the recipes call tools that are only on the PATH inside it.

| Command | What it does |
|---|---|
| `just` | lint → typecheck → test → docs, in order |
| `just lint` | `ruff format` + `desphinx --fix` + `ruff check --fix` |
| `just lint-check` | Non-mutating variant for CI |
| `just typecheck` | `pyright` |
| `just test` | `pytest` |
| `just test-cov` | `pytest` with coverage, `--cov-fail-under=90` |
| `just doctest` | Doctests in `src/` |
| `just docs` | `docs-example` (run the CLI on the example), then `zensical build` |
| `just release` | Tag the `pyproject.toml` version and publish a GitHub release for it, publishing to PyPI |

Setup: `uv sync`.

## Releasing

Every PR merges to `main`; a release is a tag on it, made by the maintainer only.

1. `uv version --bump rc` (`0.2.0.dev1` → `0.2.0rc1`, `0.2.0rc1` → `0.2.0rc2`), or `--bump stable` for a full release, and commit it to `main`.
2. `just release`, which refuses a dev version, a dirty tree, or a `main` that differs from `origin/main`.
3. After a full release, `uv version --bump minor --bump dev` and commit, so a git install of `main` does not report the released version.
   After a pre-release, `main` keeps reporting the rc version until the next bump; that is accepted.

A pre-release lets downstream projects test unreleased work from PyPI, by asking for it explicitly (`>=0.2.0rc1`), while everyone else keeps the last stable release.

The docs site deploys only on a stable release, so it documents what PyPI serves.
To rebuild a release's docs: `gh workflow run docs.yml -f ref=v0.2.0`.
Running it without `ref` deploys `main`, so the site then documents unreleased work; to publish a docs fix properly, release a patch.

TestPyPI is manual only (Actions → "Publish to PyPI" → testpypi), as a dry run after changing the publish workflow or the build.

## Toolchain

uv (packaging), just (tasks), ruff (format + lint), pyright (types), pytest (tests), zensical + mkdocstrings (docs), pre-commit, GitHub Actions.

## Conventions

- Ruff `select` is explicit, never left to defaults — see the comment in `pyproject.toml`.
- Docstrings are required in `src/` (google convention) and exempt in `tests/`.
- Tool versions are pinned in three places that must stay in step: `[dependency-groups] dev`, `.pre-commit-config.yaml` revs, and the `uv_build` bound in `[build-system]`.

## This project was generated from a template

The answers are in `.copier-answers.yml`. `copier update` pulls later template
changes in; it uses that file to replay the original answers, so keep it
committed and don't hand-edit it.
