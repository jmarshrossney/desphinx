"""Find and fix reStructuredText and Sphinx markup in Python source.

Only docstrings and comments are examined. A docstring here is any statement
that is a bare string literal, which covers module, class and function
docstrings as well as attribute docstrings below an assignment. Runtime strings,
such as error messages, are never examined or changed.

Inside a docstring, fenced code blocks and doctest lines are skipped.
"""

import ast
import io
import re
import tokenize
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from typing import TypeGuard

from desphinx.blocks import DIRECTIVE, FIELD, LITERAL_BLOCK, rewrite

__all__ = ["RULES", "Finding", "Rule", "check", "fix"]


class Where(Enum):
    """The kinds of text a rule applies to."""

    DOCSTRING = "docstring"
    COMMENT = "comment"


@dataclass(frozen=True)
class Rule:
    """One kind of reStructuredText markup, and the Markdown to use instead.

    Attributes:
        code: Stable identifier, used in output and to select rules.
        summary: What the rule catches.
        instead: What to write instead, shown alongside each finding.
        pattern: Matches the offending markup within one line.
        where: The kinds of text the rule applies to.
        fixable: Whether `fix` rewrites it, in at least some cases.
    """

    code: str
    summary: str
    instead: str
    pattern: re.Pattern[str]
    where: frozenset[Where]
    fixable: bool


BOTH = frozenset(Where)
DOCSTRING = frozenset({Where.DOCSTRING})
COMMENT = frozenset({Where.COMMENT})

_ROLE = re.compile(r":(?:[a-z]+:)?[a-z]+:`([^`]+)`")
# A pair where there is one, so each literal is reported once.
_DOUBLE_BACKTICK = re.compile(r"(?<!`)``(?!`)(?:[^`\n]+?(?<!`)``(?!`))?")
_DOUBLE_BACKTICK_PAIR = re.compile(r"(?<!`)``(?!`)([^`\n]+?)(?<!`)``(?!`)")
_HYPERLINK = re.compile(r"`([^`<]+?)\s*<([^`>]+)>`__?")
# The tail alone, so a link whose text and target are on different lines is found.
_HYPERLINK_TAIL = re.compile(r"<[^`>\s]+>`__?")
_ATTRIBUTE_COMMENT = re.compile(r"^#:")

RULES: tuple[Rule, ...] = (
    Rule(
        "RST001",
        "Sphinx role",
        "`name`, or [`name`][dotted.path] to link to an object",
        _ROLE,
        BOTH,
        fixable=True,
    ),
    Rule(
        "RST002",
        "reST directive",
        "an admonition such as `!!! warning`, or plain prose",
        DIRECTIVE,
        DOCSTRING,
        fixable=True,
    ),
    Rule(
        "RST003",
        "reST literal block",
        "a fenced code block",
        LITERAL_BLOCK,
        DOCSTRING,
        fixable=True,
    ),
    Rule(
        "RST004",
        "reST double-backtick literal",
        "single backticks",
        _DOUBLE_BACKTICK,
        BOTH,
        fixable=True,
    ),
    Rule(
        "RST005",
        "reST hyperlink",
        "[text](url)",
        _HYPERLINK_TAIL,
        BOTH,
        fixable=True,
    ),
    Rule(
        "RST006",
        "Sphinx field list",
        "the sections of the docstring style the project uses",
        FIELD,
        DOCSTRING,
        fixable=True,
    ),
    Rule(
        "RST007",
        "Sphinx attribute comment",
        "a docstring on the line after the assignment",
        _ATTRIBUTE_COMMENT,
        COMMENT,
        fixable=True,
    ),
)


@dataclass(frozen=True, order=True)
class Finding:
    """One rule matched on one line.

    Attributes:
        line: 1-based line number.
        column: 0-based column of the match.
        rule: The rule that matched.
    """

    line: int
    column: int
    rule: Rule

    def __str__(self) -> str:
        """Format as `line:column: CODE summary; use instead`."""
        r = self.rule
        return f"{self.line}:{self.column + 1}: {r.code} {r.summary}; use {r.instead}"


@dataclass(frozen=True)
class _Span:
    """The examined part of one line: from `start` to the end of the line."""

    line: int
    start: int
    where: Where


def _is_docstring(node: ast.AST | None) -> TypeGuard[ast.Expr]:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _spans(source: str) -> Iterator[_Span]:
    lines = source.splitlines()
    for node in ast.walk(ast.parse(source)):
        if not _is_docstring(node):
            continue
        in_fence = False
        last = node.end_lineno or node.lineno
        for i in range(node.lineno, last + 1):
            text = lines[i - 1]
            stripped = text.lstrip()
            if stripped.startswith(("```", '"""```', "'''```")):
                in_fence = not in_fence
                continue
            if in_fence or stripped.startswith((">>> ", "... ")):
                continue
            start = node.col_offset if i == node.lineno else 0
            yield _Span(i, start, Where.DOCSTRING)
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT:
            yield _Span(tok.start[0], tok.start[1], Where.COMMENT)


def check(source: str, *, style: str | None = None) -> list[Finding]:
    """Find reStructuredText and Sphinx markup in Python source.

    Args:
        source: The contents of a Python file.
        style: The project's docstring style. With `"sphinx"`, field lists are
            the expected markup and RST006 is not reported.

    Returns:
        Every match, sorted by position. A run of attribute comments is reported
        once, at its first line.

    Raises:
        SyntaxError: If `source` is not valid Python.
    """
    lines = source.splitlines()
    found = set()
    for span in _spans(source):
        text = lines[span.line - 1][span.start :]
        for rule in RULES:
            if span.where not in rule.where:
                continue
            if rule.pattern is FIELD and style == "sphinx":
                continue
            if rule.pattern is LITERAL_BLOCK and DIRECTIVE.search(text):
                continue
            if (
                rule.pattern is _ATTRIBUTE_COMMENT
                and span.line > 1
                and lines[span.line - 2].lstrip().startswith("#:")
            ):
                continue
            for m in rule.pattern.finditer(text):
                found.add(Finding(span.line, span.start + m.start(), rule))
    return sorted(found, key=lambda f: (f.line, f.column, f.rule.code))


def _role_text(match: re.Match[str]) -> str:
    target = match.group(1)
    if m := re.fullmatch(r"(.+?)\s*<[^>]+>", target):
        return f"`{m.group(1)}`"
    if target.startswith("~"):
        return f"`{target[1:].rsplit('.', 1)[-1]}`"
    return f"`{target.lstrip('!')}`"


def _fix_text(text: str) -> str:
    text = _ROLE.sub(_role_text, text)
    text = _HYPERLINK.sub(r"[\1](\2)", text)
    return _DOUBLE_BACKTICK_PAIR.sub(r"`\1`", text)


def _newline(line: str) -> str:
    return "\r\n" if line.endswith("\r\n") else "\n"


def _fix_lines(source: str) -> str:
    lines = source.splitlines(keepends=True)
    for span in _spans(source):
        line = lines[span.line - 1]
        head, tail = line[: span.start], line[span.start :]
        lines[span.line - 1] = head + _fix_text(tail)
    return "".join(lines)


def _following(tree: ast.AST) -> dict[ast.AST, ast.AST | None]:
    """Map each statement to the statement after it in the same block."""
    after: dict[ast.AST, ast.AST | None] = {}
    for node in ast.walk(tree):
        for _, value in ast.iter_fields(node):
            if isinstance(value, list) and value and isinstance(value[0], ast.stmt):
                for stmt, nxt in zip(value, [*value[1:], None], strict=True):
                    after[stmt] = nxt
    return after


def _fix_attribute_comments(source: str) -> str:
    """Move each run of `#:` comments to a docstring below its assignment."""
    lines = source.splitlines(keepends=True)
    tree = ast.parse(source)
    after = _following(tree)
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        if not all(isinstance(t, ast.Name | ast.Attribute) for t in targets):
            continue
        last = node.end_lineno or node.lineno
        rest = lines[last - 1][node.end_col_offset :].strip()
        if rest and not rest.startswith("#"):
            continue
        if (nxt := after.get(node)) is not None and _is_docstring(nxt):
            continue
        pad = lines[node.lineno - 1][: node.col_offset]
        first = node.lineno
        while first > 1 and lines[first - 2].startswith(pad + "#:"):
            first -= 1
        text = [
            lines[i][len(pad) + 2 :].rstrip().removeprefix(" ")
            for i in range(first - 1, node.lineno - 1)
        ]
        if not text or not text[0] or any('"""' in t or "\\" in t for t in text):
            continue
        edits.append((first, node.lineno, last, pad, text))
    for first, start, last, pad, text in sorted(edits, reverse=True):
        nl = _newline(lines[last - 1])
        if not lines[last - 1].endswith("\n"):
            lines[last - 1] += nl
        if len(text) == 1 and not text[0].endswith('"'):
            doc = [f'{pad}"""{text[0]}"""{nl}']
        else:
            body = [f"{pad}{t}{nl}" if t else nl for t in text[1:]]
            doc = [f'{pad}"""{text[0]}{nl}', *body, f'{pad}"""{nl}']
        lines[last:last] = doc
        del lines[first - 1 : start - 1]
    return "".join(lines)


def _fix_docstring_blocks(source: str, style: str | None, unsafe: bool) -> str:
    lines = source.splitlines(keepends=True)
    tree = ast.parse(source)
    returns: dict[ast.AST, str] = {}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            and node.returns
            and _is_docstring(node.body[0])
        ):
            returns[node.body[0]] = ast.unparse(node.returns)
    docstrings = [n for n in ast.walk(tree) if _is_docstring(n)]
    for node in sorted(docstrings, key=lambda n: n.lineno, reverse=True):
        first, last = node.lineno, node.end_lineno or node.lineno
        if last - first < 2 or lines[last - 1].strip() not in ('"""', "'''"):
            continue
        interior = [line.rstrip("\r\n") for line in lines[first : last - 1]]
        new = rewrite(interior, style=style, unsafe=unsafe, returns=returns.get(node))
        if new != interior:
            nl = _newline(lines[first])
            lines[first : last - 1] = [line + nl for line in new]
    return "".join(lines)


def fix(source: str, *, style: str | None = None, unsafe: bool = False) -> str:
    """Rewrite the markup that has one Markdown equivalent.

    Rewrites Sphinx roles to inline code, reST hyperlinks to Markdown links,
    double-backtick literals to single backticks, `#:` comments to docstrings
    below the assignment, admonition directives to `!!!` admonitions, and code
    directives that name a language to fenced blocks. Everything else is left
    for `check` to report.

    Args:
        source: The contents of a Python file.
        style: The docstring style to rewrite Sphinx field lists to, `"google"`
            or `"numpy"`. Field lists are left alone otherwise.
        unsafe: Also rewrite literal blocks, and code directives with no
            language, to fenced blocks marked `python`. Sphinx highlights them
            as Python by default, but the docstring does not say so.

    Returns:
        The rewritten source, identical to `source` if nothing applied.

    Raises:
        SyntaxError: If `source` is not valid Python.
    """
    source = _fix_lines(source)
    source = _fix_attribute_comments(source)
    return _fix_docstring_blocks(source, style, unsafe)
