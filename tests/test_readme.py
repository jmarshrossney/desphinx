import re
from pathlib import Path

from markdown_docstrings import RULES

README = Path(__file__).parent.parent / "README.md"
ROWS = re.findall(r"^\| (RST\d{3}) \|.*\| ([^|]+) \|$", README.read_text(), re.M)


def test_readme_lists_every_rule_once():
    assert [code for code, _ in ROWS] == [r.code for r in RULES]


def test_readme_fix_column_matches_rules():
    fixable = {r.code: r.fixable for r in RULES}
    assert {code: fix.strip() != "no" for code, fix in ROWS} == fixable
