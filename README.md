# desphinx

`desphinx` finds and fixes reStructuredText and Sphinx markup in Python docstrings and comments, for projects whose API reference is Markdown rendered by mkdocstrings (Zensical, MkDocs).

This exists because I got fed up with coding agents constantly reintroducing reST/Sphinx into docstrings, sometimes in spite of instructions to the contrary in `AGENTS.md`.

Please see the [documentation](https://jmarshrossney.github.io/desphinx) for user instructions (also below) and an example.

## Installation and usage

### pre-commit

```yaml
- repo: https://github.com/jmarshrossney/desphinx
  rev: <tag or commit>
  hooks:
    - id: desphinx
      args: [--fix]
```

### Command line

```sh
uvx --from git+https://github.com/jmarshrossney/desphinx desphinx src tests
```

### CI

Add it to the dev dependency group:

```sh
uv add --dev "desphinx @ git+https://github.com/jmarshrossney/desphinx"
```

and run it from the lint task, so commits made without the hook are caught too:

```just
lint-check:
  desphinx src tests
```

### Output

Each finding is printed as `path:line:column: CODE summary; use instead`.
The exit status is 1 if anything was reported or rewritten.
Directories are searched recursively, skipping hidden directories and `__pycache__`, `node_modules`, `site`, `build` and `dist`; `--exclude GLOB` skips more.

`--fix` rewrites the markup that has a clear Markdown equivalent and reports the rest, with suggested replacements.

## Rules

<!-- --8<-- [start:rules] -->
| Code | Catches | Where | `--fix` |
|---|---|---|---|
| RST001 | Sphinx roles, e.g. `:func:` followed by a backticked name | docstrings, comments | to inline code |
| RST002 | reST directives, e.g. `.. warning::` | docstrings | no |
| RST003 | reST literal blocks: a line ending in `::` | docstrings | no |
| RST004 | reST double-backtick literals | docstrings, comments | to single backticks |
| RST005 | reST hyperlinks: backticked `text <url>` followed by `_` | docstrings, comments | to `[text](url)` |
| RST006 | Sphinx field lists, e.g. `:param x:` | docstrings | no |
| RST007 | Sphinx attribute comments, `#:` | comments | private names only, to `#` |
<!-- --8<-- [end:rules] -->

A docstring is any statement that is a bare string literal, so attribute docstrings are included.
Runtime strings such as error messages are never examined.
Fenced code blocks and doctest lines inside docstrings are skipped.

## Development

Install the project and its development dependencies, then run the full check suite.

```sh
uv sync
uv run just
```

See [CONTRIBUTING.md](CONTRIBUTING.md).
