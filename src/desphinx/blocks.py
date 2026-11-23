"""Rewrite multi-line reStructuredText constructs inside one docstring.

Each rewriter takes the docstring's lines, without line endings and without the
lines holding the opening and closing quotes, and returns Markdown lines, or
`None` when the construct has no single Markdown equivalent. Whatever is left
unchanged is reported by `check`.
"""

import re
import textwrap
from dataclasses import dataclass, field

__all__ = ["DIRECTIVE", "FIELD", "LITERAL_BLOCK", "rewrite"]

DIRECTIVE = re.compile(r"^\s*\.\. [a-z][a-z-]*::")
LITERAL_BLOCK = re.compile(r"(?<!:)::\s*$")
FIELD = re.compile(
    r"^\s*:(?:param|parameter|arg|argument|key|keyword|type|returns?|rtype"
    r"|raises?|except|exception|var|ivar|cvar|vartype|yields?|ytype)\b[^:]*:"
)

_DIRECTIVE_PARTS = re.compile(r"^(\s*)\.\. ([a-z][a-z-]*)::(?:\s+(.*?))?\s*$")
_OPTION = re.compile(r"^:[a-z-]+:(?:\s|$)")
_ANY_FIELD = re.compile(r"^(\s*):([a-z]+)(?:\s+([^:]*?))?\s*:(?:\s+(.*?))?\s*$")

_ADMONITIONS = frozenset(
    {
        "attention",
        "caution",
        "danger",
        "error",
        "hint",
        "important",
        "note",
        "tip",
        "warning",
    }
)
_VERSIONED = {
    "versionadded": ("note", "Added in version"),
    "versionchanged": ("note", "Changed in version"),
    "deprecated": ("warning", "Deprecated since version"),
}
_CODE = frozenset({"code", "code-block", "sourcecode"})

_PARAM = frozenset({"param", "parameter", "arg", "argument", "key", "keyword"})
_RETURN = frozenset({"returns", "return"})
_YIELD = frozenset({"yields", "yield"})
_RAISE = frozenset({"raises", "raise", "except", "exception"})
_VAR = frozenset({"var", "ivar", "cvar"})


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _block(lines: list[str], i: int, indent: int) -> tuple[list[str], int]:
    """The lines after `lines[i]` indented deeper than `indent`, dedented.

    Blank lines inside the block are kept; trailing blank lines are not part of
    it. Returns the block and the index of the first line after it.
    """
    end = j = i + 1
    while j < len(lines) and (not lines[j].strip() or _indent(lines[j]) > indent):
        if lines[j].strip():
            end = j + 1
        j += 1
    body = textwrap.dedent("\n".join(lines[i + 1 : end])).split("\n")
    return (body if end > i + 1 else []), end


def _indented(lines: list[str], indent: int) -> list[str]:
    pad = " " * indent
    return [pad + line if line.strip() else "" for line in lines]


def _strip_blank(lines: list[str]) -> list[str]:
    while lines and not lines[0].strip():
        lines = lines[1:]
    while lines and not lines[-1].strip():
        lines = lines[:-1]
    return lines


def _fence(lang: str, body: list[str], indent: int) -> list[str]:
    pad = " " * indent
    return [f"{pad}```{lang}", *_indented(body, indent), f"{pad}```"]


def _directive(lines: list[str], i: int, unsafe: bool) -> tuple[list[str], int] | None:
    m = _DIRECTIVE_PARTS.match(lines[i])
    if not m:
        return None
    pad, name, arg = m[1], m[2], m[3] or ""
    indent = len(pad)
    raw, end = _block(lines, i, indent)
    body = _strip_blank(raw)
    unchanged = lines[i:end], end
    if body and _OPTION.match(body[0]):
        return unchanged
    if name in _CODE:
        lang = arg or ("python" if unsafe else "")
        if not lang or " " in lang or not body:
            return unchanged
        return _fence(lang, body, indent), end
    if name in _ADMONITIONS:
        kind, title, content = name, "", [arg, *raw] if arg else body
    elif name == "seealso":
        kind, title, content = "note", "See also", [arg, *raw] if arg else body
    elif name in _VERSIONED:
        version, _, rest = arg.partition(" ")
        if not version:
            return unchanged
        kind, prefix = _VERSIONED[name]
        title, content = f"{prefix} {version}", [rest, *raw] if rest else body
    elif name == "admonition" and arg:
        kind, title, content = "note", arg, body
    else:
        return unchanged
    if '"' in title or (not content and not title):
        return unchanged
    header = f"{pad}!!! {kind}" + (f' "{title}"' if title else "")
    content = rewrite(content, unsafe=unsafe)
    return [header, *_indented(content, indent + 4)], end


def _literal_block(lines: list[str], i: int) -> tuple[list[str], int] | None:
    line = lines[i]
    if DIRECTIVE.match(line) or not LITERAL_BLOCK.search(line):
        return None
    if i + 1 >= len(lines) or lines[i + 1].strip():
        return None
    indent = _indent(line)
    body, end = _block(lines, i, indent)
    body = _strip_blank(body)
    if not body:
        return None
    text = line.rstrip()
    if text.strip() == "::":
        head = []
    elif text[:-2].endswith((" ", "\t")):
        head = [text[:-2].rstrip(), ""]
    else:
        head = [text[:-1], ""]
    return [*head, *_fence("python", body, indent)], end


@dataclass
class _Item:
    name: str = ""
    type: str = ""
    desc: list[str] = field(default_factory=list)


@dataclass
class _Fields:
    params: dict[str, _Item] = field(default_factory=dict)
    returns: _Item | None = None
    yields: _Item | None = None
    raises: list[_Item] = field(default_factory=list)
    attributes: dict[str, _Item] = field(default_factory=dict)


def _split_name(arg: str) -> tuple[str, str] | None:
    """Split `type name` or `name` into `(name, type)`."""
    words = arg.split()
    if not words:
        return None
    return words[-1], " ".join(words[:-1])


def _parse_fields(
    entries: list[tuple[str, str, list[str]]],
) -> _Fields | None:
    out = _Fields()
    types: dict[str, str] = {}
    vartypes: dict[str, str] = {}
    rtype = ytype = None
    for kind, arg, desc in entries:
        one_line = " ".join(d.strip() for d in desc).strip()
        if kind in _PARAM or kind in _VAR:
            split = _split_name(arg)
            if split is None:
                return None
            name, type_ = split
            target = out.params if kind in _PARAM else out.attributes
            if name in target:
                return None
            target[name] = _Item(name, type_, desc)
        elif kind == "type" or kind == "vartype":
            if not arg or " " in arg.strip() or not one_line:
                return None
            (types if kind == "type" else vartypes)[arg.strip()] = one_line
        elif kind in _RETURN or kind in _YIELD:
            if arg:
                return None
            item = _Item(desc=desc)
            if kind in _RETURN:
                out.returns = item
            else:
                out.yields = item
        elif kind == "rtype" or kind == "ytype":
            if arg or not one_line:
                return None
            if kind == "rtype":
                rtype = one_line
            else:
                ytype = one_line
        elif kind in _RAISE:
            if not arg:
                return None
            out.raises.append(_Item(type=arg.strip(), desc=desc))
        else:
            return None
    for name, type_ in types.items():
        if name not in out.params or out.params[name].type:
            return None
        out.params[name].type = type_
    for name, type_ in vartypes.items():
        if name not in out.attributes or out.attributes[name].type:
            return None
        out.attributes[name].type = type_
    if rtype:
        out.returns = out.returns or _Item()
        out.returns.type = rtype
    if ytype:
        out.yields = out.yields or _Item()
        out.yields.type = ytype
    return out


def _desc_lines(desc: list[str]) -> list[str]:
    return _strip_blank(textwrap.dedent("\n".join(desc)).split("\n"))


def _google_item(head: str, desc: list[str]) -> list[str]:
    lines = _desc_lines(desc)
    if not lines:
        return [f"    {head}"]
    first = f"    {head}: {lines[0]}" if head else f"    {lines[0]}"
    return [first, *_indented(lines[1:], 8)]


def _google(f: _Fields) -> list[list[str]]:
    sections = []
    if f.params:
        items = [
            _google_item(f"{p.name} ({p.type})" if p.type else p.name, p.desc)
            for p in f.params.values()
        ]
        sections.append(["Args:", *(line for item in items for line in item)])
    for title, item in (("Returns:", f.returns), ("Yields:", f.yields)):
        if item:
            head = f"({item.type})" if item.type else ""
            sections.append([title, *_google_item(head, item.desc)])
    if f.raises:
        items = [_google_item(r.type, r.desc) for r in f.raises]
        sections.append(["Raises:", *(line for item in items for line in item)])
    if f.attributes:
        items = [
            _google_item(f"{a.name} ({a.type})" if a.type else a.name, a.desc)
            for a in f.attributes.values()
        ]
        sections.append(["Attributes:", *(line for item in items for line in item)])
    return sections


def _numpy_item(head: str, desc: list[str]) -> list[str]:
    return [head, *_indented(_desc_lines(desc), 4)]


def _numpy(f: _Fields, returns: str | None) -> list[list[str]] | None:
    def section(title: str, items: list[list[str]]) -> list[str]:
        return [title, "-" * len(title), *(line for item in items for line in item)]

    sections = []
    if f.params:
        items = [
            _numpy_item(f"{p.name} : {p.type}" if p.type else p.name, p.desc)
            for p in f.params.values()
        ]
        sections.append(section("Parameters", items))
    if f.returns:
        type_ = f.returns.type or returns
        if not type_:
            return None
        sections.append(section("Returns", [_numpy_item(type_, f.returns.desc)]))
    if f.yields:
        if not f.yields.type:
            return None
        sections.append(section("Yields", [_numpy_item(f.yields.type, f.yields.desc)]))
    if f.raises:
        items = [_numpy_item(r.type, r.desc) for r in f.raises]
        sections.append(section("Raises", items))
    if f.attributes:
        items = [
            _numpy_item(f"{a.name} : {a.type}" if a.type else a.name, a.desc)
            for a in f.attributes.values()
        ]
        sections.append(section("Attributes", items))
    return sections


def _field_list(
    lines: list[str], i: int, style: str, returns: str | None
) -> tuple[list[str], int] | None:
    if not FIELD.match(lines[i]):
        return None
    indent = _indent(lines[i])
    raw: list[tuple[str, str, list[str], list[str]]] = []
    j = i
    end = i
    while j < len(lines):
        line = lines[j]
        m = _ANY_FIELD.match(line)
        if m and len(m[1]) == indent:
            raw.append((m[2], m[3] or "", [m[4]] if m[4] else [], []))
        elif line.strip() and _indent(line) > indent and raw:
            raw[-1][3].append(line)
        elif not line.strip():
            k = j
            while k < len(lines) and not lines[k].strip():
                k += 1
            nxt = _ANY_FIELD.match(lines[k]) if k < len(lines) else None
            if not (nxt and len(nxt[1]) == indent):
                break
            j = k
            continue
        else:
            break
        j += 1
        end = j
    unchanged = lines[i:end], end
    entries = [
        (kind, arg, [*first, *textwrap.dedent("\n".join(rest)).split("\n")])
        if rest
        else (kind, arg, first)
        for kind, arg, first, rest in raw
    ]
    if any(FIELD.match(line) for line in lines[:i] + lines[end:]):
        return unchanged
    # A numpy section runs to the next section header, so it would swallow
    # anything after it.
    if style == "numpy" and any(line.strip() for line in lines[end:]):
        return unchanged
    parsed = _parse_fields(entries)
    if parsed is None:
        return unchanged
    sections = _google(parsed) if style == "google" else _numpy(parsed, returns)
    if not sections:
        return unchanged
    out: list[str] = []
    for n, section in enumerate(sections):
        if n:
            out.append("")
        out.extend(_indented(section, indent))
    return out, end


def rewrite(
    lines: list[str],
    *,
    style: str | None = None,
    unsafe: bool = False,
    returns: str | None = None,
) -> list[str]:
    """Rewrite directives, literal blocks and field lists in docstring lines.

    Args:
        lines: The docstring's lines between the quotes, without line endings.
        style: The docstring style field lists are rewritten to, `"google"` or
            `"numpy"`; any other value leaves them unchanged.
        unsafe: Also rewrite literal blocks, and code directives with no
            language, to fenced blocks marked `python`.
        returns: The function's return annotation, used for a numpy `Returns`
            section when the docstring gives no return type.

    Returns:
        The rewritten lines, equal to `lines` if nothing applied.
    """
    out: list[str] = []
    i = 0
    in_fence = False
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        if stripped.startswith("```"):
            in_fence = not in_fence
        elif not in_fence and not stripped.startswith((">>> ", "... ")):
            result = _directive(lines, i, unsafe)
            if result is None and unsafe:
                result = _literal_block(lines, i)
            if result is None and style in ("google", "numpy"):
                result = _field_list(lines, i, style, returns)
            if result is not None:
                new, i = result
                out.extend(new)
                continue
        out.append(line)
        i += 1
    return out
