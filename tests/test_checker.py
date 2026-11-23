import textwrap

import pytest

from desphinx import RULES, check, fix


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
        ("#: Private.\n_X = 1\n", '_X = 1\n"""Private."""\n'),
        ("#: Public.\nX = 1\n", 'X = 1\n"""Public."""\n'),
        ("#: Annotated.\nX: int = 1\n", 'X: int = 1\n"""Annotated."""\n'),
        ("#: No newline.\nX = 1", 'X = 1\n"""No newline."""\n'),
        (
            "class A:\n    #: One.\n    #:\n    #: Two.\n    x: int\n",
            'class A:\n    x: int\n    """One.\n\n    Two.\n    """\n',
        ),
        ('#: Says "hi"\nX = 1\n', 'X = 1\n"""Says "hi"\n"""\n'),
        (
            "#: Example:\n#:   indented\nX = 1\n",
            'X = 1\n"""Example:\n  indented\n"""\n',
        ),
        (
            "#: Spans lines.\nX = (\n    1,\n)  # trailing\nY = 2\n",
            'X = (\n    1,\n)  # trailing\n"""Spans lines."""\nY = 2\n',
        ),
        (
            "class A:\n    def f(self):\n        #: Attr.\n        self.x = 1\n",
            'class A:\n    def f(self):\n        self.x = 1\n        """Attr."""\n',
        ),
        (
            'def f():\n    """Doc.\n\n    .. warning::\n       Careful.\n    """\n',
            'def f():\n    """Doc.\n\n    !!! warning\n        Careful.\n    """\n',
        ),
        (
            '"""Doc.\n\n.. code-block:: toml\n\n   a = 1\n"""\n',
            '"""Doc.\n\n```toml\na = 1\n```\n"""\n',
        ),
    ],
)
def test_fix_rewrites(before, after):
    assert fix(before) == after
    assert fix(after) == after
    assert check(after) == []


def test_fix_rewrites_field_lists_given_a_style():
    source = '"""Doc.\n\n:param x: The x.\n"""\n'
    assert fix(source) == source
    assert fix(source, style="google") == '"""Doc.\n\nArgs:\n    x: The x.\n"""\n'
    assert check(source, style="sphinx") == []


def test_unsafe_fixes_rewrite_literal_blocks():
    source = '"""Doc.\n\nExample::\n\n    x = 1\n"""\n'
    after = '"""Doc.\n\nExample:\n\n```python\nx = 1\n```\n"""\n'
    assert fix(source) == source
    assert fix(source, unsafe=True) == after
    assert check(after) == []


def test_numpy_returns_type_falls_back_to_the_annotation():
    source = 'def f() -> int:\n    """Doc.\n\n    :returns: The x.\n    """\n'
    assert fix(source, style="numpy") == (
        'def f() -> int:\n    """Doc.\n\n    Returns\n    -------\n'
        '    int\n        The x.\n    """\n'
    )


@pytest.mark.parametrize(
    "source",
    [
        '"""Example::\n\n    x = 1\n"""\n',
        "#: Not followed by an assignment.\nf()\n",
        '#: Already documented.\nX = 1\n"""Doc."""\n',
        "#: Tuple target.\nX, Y = 1, 2\n",
        "#: Two statements.\nX = 1; Y = 2\n",
        '#: Has """quotes""".\nX = 1\n',
        "#: Has a \\ backslash.\nX = 1\n",
        "X = 1  #: Trailing.\n",
        '"""Doc.\n\n.. note::\n   :class: x\n\n   Hi.\n"""\n',
        '"""Doc.\n\n.. image:: a.png\n"""\n',
        '"""Doc.\n\n.. note::\n   Hi."""\n',
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
