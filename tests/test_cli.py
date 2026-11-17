import subprocess
import sys

import pytest

from markdown_docstrings.cli import main


@pytest.fixture
def tree(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "clean.py").write_text('"""Use `x`."""\n')
    (tmp_path / "pkg" / "dirty.py").write_text('"""Use ``x``.\n\nExample::\n"""\n')
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "lib.py").write_text('"""Use ``x``."""\n')
    return tmp_path


def test_clean_file_exits_zero(tree, capsys):
    assert main([str(tree / "pkg" / "clean.py")]) == 0
    assert capsys.readouterr().out == ""


def test_findings_exit_one_and_name_the_file(tree, capsys):
    assert main([str(tree)]) == 1
    out = capsys.readouterr().out.splitlines()
    dirty = tree / "pkg" / "dirty.py"
    assert out == [
        f"{dirty}:1:8: RST004 reST double-backtick literal; use single backticks",
        f"{dirty}:3:8: RST003 reST literal block; use a fenced code block",
    ]


def test_hidden_directories_are_skipped(tree, capsys):
    main([str(tree)])
    assert ".venv" not in capsys.readouterr().out


def test_exclude(tree, capsys):
    assert main([str(tree), "--exclude", "*/dirty.py"]) == 0


def test_fix_rewrites_and_still_fails(tree, capsys):
    dirty = tree / "pkg" / "dirty.py"
    assert main(["--fix", str(dirty)]) == 1
    assert dirty.read_text() == '"""Use `x`.\n\nExample::\n"""\n'
    out = capsys.readouterr().out.splitlines()
    assert out == [
        f"{dirty}: fixed",
        f"{dirty}:3:8: RST003 reST literal block; use a fenced code block",
    ]
    assert main(["--fix", str(dirty)]) == 1


def test_fix_on_clean_file_exits_zero(tree):
    assert main(["--fix", str(tree / "pkg" / "clean.py")]) == 0


def test_invalid_python_is_skipped(tmp_path, capsys):
    bad = tmp_path / "bad.py"
    bad.write_text("def (:\n")
    assert main([str(bad)]) == 0
    assert "skipped, not valid Python" in capsys.readouterr().err


def test_runs_as_a_module(tree):
    result = subprocess.run(
        [sys.executable, "-m", "markdown_docstrings", str(tree / "pkg")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "RST003" in result.stdout


def test_own_source_is_clean():
    assert main(["src", "tests"]) == 0
