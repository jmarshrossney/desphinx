# desphinx

Find and fix reStructuredText and Sphinx markup in Python docstrings and comments, for projects whose API reference is Markdown rendered by mkdocstrings (Zensical, MkDocs).

reST creeps into docstrings, mostly from coding agents and from code copied out of Sphinx-documented projects.
mkdocstrings renders docstrings as Markdown, so most of that markup shows up verbatim in the API reference.
Attribute comments (`#:`) are worse: griffe does not read them, so the documentation silently disappears.

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

The rules without a fix need a person: a literal block needs a language for its fence, a directive needs choosing between an admonition and prose, and a public `#:` comment needs moving below the assignment and rewrapping.

Replace `vX.Y.Z` with a [release](https://github.com/jmarshrossney/desphinx/releases) tag.

## Usage

As a pre-commit hook:

```yaml
- repo: https://github.com/jmarshrossney/desphinx
  rev: <tag or commit>
  hooks:
    - id: desphinx
      args: [--fix]
```

From the command line, without installing:

```sh
uvx --from git+https://github.com/jmarshrossney/desphinx desphinx src tests
```

In CI, add it to the dev dependency group and call it from the lint task:

```sh
uv add --dev "desphinx @ git+https://github.com/jmarshrossney/desphinx"
```

```just
lint-check:
  desphinx src tests
```

The exit status is 1 if anything was reported or rewritten, as for `ruff check --fix`.
Directories are searched recursively, skipping hidden directories and `__pycache__`, `node_modules`, `site`, `build` and `dist`; `--exclude GLOB` skips more.

## Why a standalone command with a pre-commit hook

The checks started as a test in one project's suite, and the aim is to reuse them across projects that all document with Zensical.

One package with a console script serves both places a check needs to run:

- **At commit time**, as a pre-commit hook, which catches markup where it is written and can fix the mechanical cases there and then.
- **In CI**, as a step in the lint task, because a hook alone is skipped by `--no-verify` and by clones without hooks installed, and not every project runs pre-commit in CI.

It has no dependencies, so the hook installs quickly and `uvx` runs it without a project.
A git source is also unaffected by `[tool.uv] exclude-newer`, so projects using that setting need no exemption.

Alternatives considered:

| Option | Why not |
|---|---|
| A ruff rule | Ruff has no plugin system, and no existing rule covers this. |
| A pytest plugin or a copied test | Ties a lint check to the test suite, so failures arrive later than at commit time, and copies drift apart. |
| A griffe extension, warning during the docs build | Only sees objects that are rendered, so it misses comments, tests, private code and examples, which is where the habit is picked up and imitated. |
| pygrep hooks | Regular expressions over whole files cannot tell docstrings and comments from runtime strings, or skip fenced code. |

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md).
In short: `uv sync`, then `uv run just`.

---

Generated from a [Copier](https://copier.readthedocs.io/) template, recorded in `.copier-answers.yml`.
Pull later template changes with `copier update`.
