import logging
from pathlib import Path

import griffe

from desphinx import RULES, check, fix

BEFORE = Path(__file__).parent.parent / "docs" / "snippets" / "before.py"


def test_docs_example_exercises_every_rule():
    assert {f.rule.code for f in check(BEFORE.read_text())} == {r.code for r in RULES}


def test_docs_example_is_fully_fixed(caplog):
    after = fix(BEFORE.read_text(), style="google", unsafe=True)
    assert check(after) == []
    module = griffe.visit("module", Path("module.py"), after)
    caplog.set_level(logging.WARNING)
    members = [m for m in module.members.values() if not m.is_alias]
    for obj in [module, *members]:
        if obj.docstring:
            obj.docstring.parse("google")
    assert caplog.records == []
