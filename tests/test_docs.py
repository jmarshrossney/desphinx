import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
PAGES = sorted((ROOT / "docs").glob("*.md"))
GENERATED = {"docs/snippets/after.py", "docs/snippets/output.txt"}  # just docs-example
MARKER = re.compile(r'^\s*--8<-- "([^":]+)(?::([\w-]+))?"$')


def snippet_lines(page: Path) -> list[str]:
    return [line for line in page.read_text().splitlines() if re.search(r"8\s*<", line)]


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_snippet_lines_are_well_formed(page):
    assert [line for line in snippet_lines(page) if not MARKER.match(line)] == []


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_snippets_resolve(page):
    for line in snippet_lines(page):
        match = MARKER.match(line)
        assert match, line
        path, section = match.groups()
        if path in GENERATED:
            continue
        text = (ROOT / path).read_text()
        if section:
            assert f"[start:{section}]" in text, line
            assert f"[end:{section}]" in text, line
