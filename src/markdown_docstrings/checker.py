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
_DIRECTIVE = re.compile(r"^\s*\.\. [a-z][a-z-]*::")
_LITERAL_BLOCK = re.compile(r"(?:(?<=\S)|^\s*)::\s*$")
# A pair where there is one, so each literal is reported once.
_DOUBLE_BACKTICK = re.compile(r"(?<!`)``(?!`)(?:[^`\n]+?(?<!`)``(?!`))?")
_DOUBLE_BACKTICK_PAIR = re.compile(r"(?<!`)``(?!`)([^`\n]+?)(?<!`)``(?!`)")
_HYPERLINK = re.compile(r"`([^`<]+?)\s*<([^`>]+)>`__?")
# The tail alone, so a link whose text and target are on different lines is found.
_HYPERLINK_TAIL = re.compile(r"<[^`>\s]+>`__?")
_FIELD = re.compile(
    r"^\s*:(?:param|parameter|arg|argument|key|keyword|type|returns?|rtype"
    r"|raises?|except|exception|var|ivar|cvar|vartype|yields?|ytype)\b[^:]*:"
)
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
        _DIRECTIVE,
        DOCSTRING,
        fixable=False,
    ),
    Rule(
        "RST003",
        "reST literal block",
        "a fenced code block",
        _LITERAL_BLOCK,
        DOCSTRING,
        fixable=False,
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
        _FIELD,
        DOCSTRING,
        fixable=False,
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


def _spans(source: str) -> Iterator[_Span]:
    lines = source.splitlines()
    for node in ast.walk(ast.parse(source)):
        if not (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
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


def _private_attribute_comments(source: str) -> set[int]:
    """Lines of `#:` comments documenting a private name.

    Private names are not rendered, so their `#:` comments can become plain
    comments rather than docstrings.
    """
    lines = source.splitlines()
    private: set[int] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        names = [t.id for t in targets if isinstance(t, ast.Name)]
        if not names or not all(n.startswith("_") for n in names):
            continue
        i = node.lineno - 1
        while i >= 1 and lines[i - 1].lstrip().startswith("#:"):
            private.add(i)
            i -= 1
    return private


def check(source: str) -> list[Finding]:
    """Find reStructuredText and Sphinx markup in Python source.

    Args:
        source: The contents of a Python file.

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
            if rule.pattern is _LITERAL_BLOCK and _DIRECTIVE.search(text):
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


def fix(source: str) -> str:
    """Rewrite the markup that has one Markdown equivalent.

    Rewrites Sphinx roles to inline code, reST hyperlinks to Markdown links,
    double-backtick literals to single backticks, and `#:` comments on private
    names to plain comments. Everything else is left for `check` to report.

    Args:
        source: The contents of a Python file.

    Returns:
        The rewritten source, identical to `source` if nothing applied.

    Raises:
        SyntaxError: If `source` is not valid Python.
    """
    lines = source.splitlines(keepends=True)
    private = _private_attribute_comments(source)
    for span in _spans(source):
        line = lines[span.line - 1]
        head, tail = line[: span.start], line[span.start :]
        if span.where is Where.COMMENT and span.line in private:
            tail = re.sub(r"^#:", "#", tail)
        lines[span.line - 1] = head + _fix_text(tail)
    return "".join(lines)
