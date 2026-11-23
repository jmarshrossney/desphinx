# desphinx

`desphinx` finds and fixes reStructuredText and Sphinx markup in Python docstrings and comments, for projects whose API reference is Markdown rendered by mkdocstrings (Zensical, MkDocs).

This exists because I got fed up with coding agents constantly reintroducing reST/Sphinx into docstrings, sometimes in spite of instructions to the contrary in `AGENTS.md`.

## Installation and usage

=== "pre-commit"

    ```yaml
    - repo: https://github.com/jmarshrossney/desphinx
      rev: <tag or commit>
      hooks:
        - id: desphinx
          args: [--fix, --docstring-style, google]
    ```

=== "Command line"

    ```sh
    uvx --from git+https://github.com/jmarshrossney/desphinx desphinx src tests
    ```

=== "CI"

    Add it to the dev dependency group:

    ```sh
    uv add --dev "desphinx @ git+https://github.com/jmarshrossney/desphinx"
    ```

    and run it from the lint task, so commits made without the hook are caught too:

    ```just
    lint-check:
      desphinx src tests
    ```

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
See [reference](reference.md) for the rules.


## Example

Here we start with a module written with lots of reST ("Before").
The terminal output ("Terminal") and the fixed module ("After `--fix`") are produced when these docs are built, by running `desphinx` to report the findings and then `desphinx --fix --unsafe-fixes --docstring-style google` to rewrite them.

=== "Before"

    ```python
    --8<-- "docs/snippets/before.py"
    ```

=== "Terminal"

    ```console
    --8<-- "docs/snippets/output.txt"
    ```

=== "After `--fix`"

    ```python
    --8<-- "docs/snippets/after.py"
    ```

Without `--docstring-style`, the field list is left as it is and reported.
Without `--unsafe-fixes`, so is the `Example::` literal block.
Markup with no Markdown equivalent, such as `.. math::` or `.. image::`, is always reported and never rewritten.
