from pathlib import Path

from markdown_docstrings import RULES, check

BEFORE = Path(__file__).parent.parent / "docs" / "snippets" / "before.py"


def test_docs_example_exercises_every_rule():
    assert {f.rule.code for f in check(BEFORE.read_text())} == {r.code for r in RULES}
