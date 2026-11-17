"""Find and fix reStructuredText and Sphinx markup in Python docstrings and comments.

Use `check` to list findings for one file's source, and `fix` to rewrite the
markup that has one Markdown equivalent. The `markdown-docstrings` command and
pre-commit hook run both over a set of files.
"""

from markdown_docstrings.checker import RULES, Finding, Rule, check, fix

__all__ = ["RULES", "Finding", "Rule", "check", "fix"]
