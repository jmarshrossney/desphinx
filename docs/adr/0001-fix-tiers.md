# 1. What `--fix` rewrites, and the flags that widen it

## Context

`--fix` used to rewrite only inline markup (roles, double backticks, hyperlinks) and `#:` comments on private names.
Directives, literal blocks, field lists and public `#:` comments were only reported, so the home page example was left mostly unchanged.
Looking at each construct showed that most have a single Markdown equivalent once the target is fixed, and the target is narrow: mkdocstrings and griffe rendering Python-Markdown, under MkDocs or Zensical.

## Decision

A rewrite belongs to one of three tiers.

| Tier | Flag | Rewrites |
|---|---|---|
| Determined by the source | `--fix` | roles, double backticks, hyperlinks; `#:` comments to a docstring below the assignment; admonition directives to `!!!`; code directives naming a language to fences |
| Determined by the source and the project's docstring style | `--fix --docstring-style google\|numpy` | field lists to that style's sections |
| Copies a Sphinx default the source does not state | `--fix --unsafe-fixes` | literal blocks, and code directives naming no language, to fences marked `python` |

Anything else is reported and never rewritten.

- `#:` comments: griffe reads attribute docstrings only on the line after the assignment, so there is one place to move them to, and a bare string statement does nothing at runtime.
  Private names get the same treatment as public ones, since griffe renders them when a project's filters allow it.
- Admonitions: `!!! name` uses the directive's name, and Material and Zensical style the aliases Sphinx accepts (`hint`, `caution`, `error`, …).
  `seealso`, `versionadded`, `versionchanged` and `deprecated` get titles worded as Sphinx renders them.
- Field lists: the docstring style is the project's choice, so it is a flag rather than a guess.
  `--docstring-style sphinx` turns off RST006, since griffe parses Sphinx fields natively.
- Literal blocks: Sphinx highlights them as Python unless `conf.py` or a `highlight` directive says otherwise, and desphinx cannot see either.

There is no flag for the rendering engine.
MkDocs and Zensical both render docstrings through mkdocstrings and Python-Markdown, so the Markdown desphinx writes is the same for both.
The one difference, whether the `admonition` extension is enabled, is configuration and is documented instead.

## Consequences

- `--fix` changes files more than it used to, including public attribute comments in projects that relied on them being left alone.
- A numpy field list followed by prose is reported rather than rewritten: a numpy section runs to the next section header and would absorb the prose.
- Rewrites are per docstring and leave the line holding the opening quotes alone, so markup on a docstring's first line is only reported.
