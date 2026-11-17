import textwrap

import pytest

from markdown_docstrings import RULES, check, fix


def src(text: str) -> str:
    return textwrap.dedent(text).lstrip("\n")


def codes(source: str) -> list[str]:
    return [f.rule.code for f in check(src(source))]


def test_rule_codes_are_unique():
    assert len({r.code for r in RULES}) == len(RULES)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ('"""See :func:`foo`."""\n', ["RST001"]),
        ('"""See :py:class:`~a.B`."""\n', ["RST001"]),
        ("# see :data:`X`\n", ["RST001"]),
        (
            'def f():\n    """Doc.\n\n    .. warning::\n       Careful.\n    """\n',
            ["RST002"],
        ),
        ('"""Example::\n\n    x = 1\n"""\n', ["RST003"]),
        ('"""::\n\n    x = 1\n"""\n', ["RST003"]),
        ('"""Use ``x``."""\n', ["RST004"]),
        ("x = 1  # use ``x``\n", ["RST004"]),
        ('"""See `the docs <https://example.com>`_."""\n', ["RST005"]),
        ('"""Doc.\n\n:param x: the x\n:returns: y\n"""\n', ["RST006", "RST006"]),
        ("#: The answer.\nX = 42\n", ["RST007"]),
    ],
)
def test_each_rule_reports(source, expected):
    assert codes(source) == expected


@pytest.mark.parametrize(
    "source",
    [
        '"""Use `x`, or [`X`][pkg.X]."""\n',
        '"""Doc.\n\n!!! warning\n    Careful.\n"""\n',
        '"""Doc.\n\n```toml\nkey = "``a``"  # .. note::\n```\n"""\n',
        '"""Doc.\n\n>>> f(":func:`x`")\n"""\n',
        'raise ValueError("bad ``x``")\n',
        'MSG = """:func:`x`"""\n',
        '"""Run `pytest tests/test_x.py::test_y`."""\n',
        '"""Fenced code uses ```python fences```."""\n',
        "# A plain comment.\nX = 1\n",
        '"""Ratio is 1:2, see https://example.com:8080/path."""\n',
    ],
)
def test_markdown_and_runtime_strings_are_clean(source):
    assert check(source) == []


def test_findings_carry_position():
    [finding] = check('def f():\n    """Use ``x``."""\n')
    assert (finding.line, finding.column) == (2, 11)
    assert str(finding).startswith("2:12: RST004 ")


def test_hyperlink_split_across_lines_is_reported_but_not_fixed():
    source = '"""See `the docs\n<https://example.com>`_ for more."""\n'
    assert codes(source) == ["RST005"]
    assert fix(source) == source


def test_attribute_comment_run_is_reported_once():
    assert codes("class A:\n    #: One.\n    #: Two.\n    x: int\n") == ["RST007"]


def test_directive_is_not_also_a_literal_block():
    assert codes('"""Doc.\n\n.. note::\n   Hi.\n"""\n') == ["RST002"]


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ('"""See :func:`foo`."""\n', '"""See `foo`."""\n'),
        ('"""See :class:`~a.b.C`."""\n', '"""See `C`."""\n'),
        ('"""See :ref:`Title <label>`."""\n', '"""See `Title`."""\n'),
        ('"""Use ``x`` and ``y``."""\n', '"""Use `x` and `y`."""\n'),
        ("x = 1  # use ``x``\n", "x = 1  # use `x`\n"),
        (
            '"""See `the docs <https://example.com>`_."""\n',
            '"""See [the docs](https://example.com)."""\n',
        ),
        ("#: Private.\n_X = 1\n", "# Private.\n_X = 1\n"),
    ],
)
def test_fix_rewrites(before, after):
    assert fix(before) == after
    assert check(after) == []


@pytest.mark.parametrize(
    "source",
    [
        "#: Public, so it needs moving to a docstring.\nX = 1\n",
        '"""Example::\n\n    x = 1\n"""\n',
        '"""Doc.\n\n```python\nf("``x``")\n```\n"""\n',
        'raise ValueError("bad ``x``")\n',
        '"""Literal with a backtick: `` ` ``."""\n',
    ],
)
def test_fix_leaves_what_it_cannot_rewrite_safely(source):
    assert fix(source) == source


def test_fix_keeps_code_before_a_comment():
    assert fix("y = '``a``'  # ``b``\n") == "y = '``a``'  # `b`\n"


def test_invalid_python_raises():
    with pytest.raises(SyntaxError):
        check("def (:\n")
