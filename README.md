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
      args: [--fix, --docstring-style, google]
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

- `--docstring-style google|numpy` lets `--fix` rewrite Sphinx field lists into that style's sections.
  With `numpy`, a field list followed by more prose is reported instead, since a numpy section runs to the next section header.
  `--docstring-style sphinx` stops field lists being reported at all, for projects that render them with mkdocstrings' Sphinx parser.
- `--unsafe-fixes` also rewrites literal blocks, and code directives that name no language, to fenced blocks marked `python`.
  That is Sphinx's default highlighting, but nothing in the docstring says the code is Python.

Admonitions are written as `!!! note`, which needs the `admonition` Markdown extension.

## Rules

<!-- --8<-- [start:rules] -->
| Code | Catches | Where | `--fix` |
|---|---|---|---|
| RST001 | Sphinx roles, e.g. `:func:` followed by a backticked name | docstrings, comments | to inline code |
| RST002 | reST directives, e.g. `.. warning::` | docstrings | admonitions to `!!!`, code blocks naming a language to fences |
| RST003 | reST literal blocks: a line ending in `::` | docstrings | with `--unsafe-fixes`, to a `python` fence |
| RST004 | reST double-backtick literals | docstrings, comments | to single backticks |
| RST005 | reST hyperlinks: backticked `text <url>` followed by `_` | docstrings, comments | to `[text](url)` |
| RST006 | Sphinx field lists, e.g. `:param x:` | docstrings | with `--docstring-style`, to its sections |
| RST007 | Sphinx attribute comments, `#:` | comments | to a docstring below the assignment |
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
