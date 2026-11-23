import pytest

from desphinx.blocks import rewrite


def lines(text: str) -> list[str]:
    return text.split("\n")


@pytest.mark.parametrize(
    ("before", "after"),
    [
        (".. note::\n   Hi.", "!!! note\n    Hi."),
        (".. tip:: Inline.\n\n   More.", "!!! tip\n    Inline.\n\n    More."),
        (".. seealso:: `x`", '!!! note "See also"\n    `x`'),
        (".. versionadded:: 1.2", '!!! note "Added in version 1.2"'),
        (
            ".. versionchanged:: 1.2 Now lazy.",
            '!!! note "Changed in version 1.2"\n    Now lazy.',
        ),
        (
            ".. deprecated:: 2.0\n   Use `g`.",
            '!!! warning "Deprecated since version 2.0"\n    Use `g`.',
        ),
        (".. admonition:: Aside\n\n   Text.", '!!! note "Aside"\n    Text.'),
        (
            "  .. warning::\n     Deep.\n\n  After.",
            "  !!! warning\n      Deep.\n\n  After.",
        ),
        (".. code:: sh\n\n   ls\n     -la", "```sh\nls\n  -la\n```"),
    ],
)
def test_directives(before, after):
    assert rewrite(lines(before)) == lines(after)


@pytest.mark.parametrize(
    "source",
    [
        ".. code-block::\n\n   x = 1",
        ".. code-block:: python\n   :linenos:\n\n   x = 1",
        ".. admonition::\n   No title.",
        '.. admonition:: Say "hi"\n   Quoted title.',
        ".. note::",
        ".. math::\n   x^2",
        "```\n.. note::\n   In a fence.\n```",
    ],
)
def test_directives_left_alone(source):
    assert rewrite(lines(source)) == lines(source)


def test_markup_nested_in_an_admonition_is_rewritten():
    source = lines(".. note::\n   Like this::\n\n       x = 1")
    assert rewrite(source, unsafe=True) == lines(
        "!!! note\n    Like this:\n\n    ```python\n    x = 1\n    ```"
    )


def test_code_directive_without_language_is_unsafe():
    source = lines(".. code-block::\n\n   x = 1")
    assert rewrite(source, unsafe=True) == lines("```python\nx = 1\n```")


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ("Example::\n\n    x = 1", "Example:\n\n```python\nx = 1\n```"),
        ("Example ::\n\n    x = 1", "Example\n\n```python\nx = 1\n```"),
        (
            "Text.\n\n::\n\n    x = 1\n\nAfter.",
            "Text.\n\n```python\nx = 1\n```\n\nAfter.",
        ),
    ],
)
def test_literal_blocks(before, after):
    assert rewrite(lines(before)) == lines(before)
    assert rewrite(lines(before), unsafe=True) == lines(after)


@pytest.mark.parametrize(
    "source", ["Example::", "Example::\n    x = 1", "Example::\n\nx"]
)
def test_literal_blocks_left_alone(source):
    assert rewrite(lines(source), unsafe=True) == lines(source)


FIELDS = (
    ":param x: The x.\n"
    ":type x: int\n"
    ":param str y: The y,\n"
    "    over two lines.\n"
    "\n"
    ":param z: The z.\n"
    ":returns: The sum.\n"
    ":rtype: float\n"
    ":raises ValueError: If bad."
)


def test_fields_google():
    assert rewrite(lines(FIELDS), style="google") == lines(
        "Args:\n"
        "    x (int): The x.\n"
        "    y (str): The y,\n"
        "        over two lines.\n"
        "    z: The z.\n"
        "\n"
        "Returns:\n"
        "    (float): The sum.\n"
        "\n"
        "Raises:\n"
        "    ValueError: If bad."
    )


def test_fields_numpy():
    assert rewrite(lines(FIELDS), style="numpy") == lines(
        "Parameters\n"
        "----------\n"
        "x : int\n"
        "    The x.\n"
        "y : str\n"
        "    The y,\n"
        "    over two lines.\n"
        "z\n"
        "    The z.\n"
        "\n"
        "Returns\n"
        "-------\n"
        "float\n"
        "    The sum.\n"
        "\n"
        "Raises\n"
        "------\n"
        "ValueError\n"
        "    If bad."
    )


def test_fields_attributes_and_yields():
    source = lines(":ivar a: The a.\n:vartype a: int\n:yields: Items.\n:ytype: str")
    assert rewrite(source, style="google") == lines(
        "Yields:\n    (str): Items.\n\nAttributes:\n    a (int): The a."
    )


def test_fields_keep_prose_after_them_in_google():
    source = lines(":param x: The x.\n\n.. note::\n   Hi.")
    assert rewrite(source, style="google") == lines(
        "Args:\n    x: The x.\n\n!!! note\n    Hi."
    )


@pytest.mark.parametrize(
    ("source", "style"),
    [
        (FIELDS, None),
        (FIELDS, "sphinx"),
        (":param x: The x.\n:meta private:", "google"),
        (":type x: int", "google"),
        (":param x: A.\n:param x: B.", "google"),
        (":param: Nameless.", "google"),
        (":raises: Untyped.", "google"),
        (":returns x: Named.", "google"),
        (":param x: The x.\n\nProse.\n\n:param y: The y.", "google"),
        (":param x: The x.\n\nProse.", "numpy"),
        (":returns: No type or annotation.", "numpy"),
        (":yields: No type.", "numpy"),
    ],
)
def test_fields_left_alone(source, style):
    assert rewrite(lines(source), style=style) == lines(source)
