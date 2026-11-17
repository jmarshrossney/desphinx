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
          args: [--fix]
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
See [reference](reference.md) for the rules.


## Example

Here we start with a module written with lots of reST ("Before").
The terminal output ("Terminal") and the fixed module ("After `--fix`") are produced by running `desphinx --fix` when these docs are built.

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

`--fix` rewrote the roles, the double-backtick literals, the hyperlink and the attribute comment on the private name.

**Not everything can be safely fixed automatically.**
The remaining findings need a decision: here, a language for the fenced block, an admonition or prose for the warning, the project's docstring sections for the field list, and where to put the docstring for `RATE_AGGREGATIONS`.
