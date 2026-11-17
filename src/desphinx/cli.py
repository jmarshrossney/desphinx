"""Command line interface.

Run `desphinx PATH...` to report markup in the Python files under
each path, or add `--fix` to rewrite what can be rewritten first. The exit
status is 1 if anything was reported or rewritten, as for `ruff check --fix`.
"""

import argparse
import fnmatch
import sys
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path

from desphinx.checker import RULES, check, fix

__all__ = ["main"]

_SKIP_DIRS = {"__pycache__", "node_modules", "site", "build", "dist"}


def _python_files(paths: Iterable[Path], exclude: Sequence[str]) -> Iterator[Path]:
    def excluded(p: Path) -> bool:
        return any(fnmatch.fnmatch(p.as_posix(), pattern) for pattern in exclude)

    for path in paths:
        if path.is_dir():
            for p in sorted(path.rglob("*.py")):
                parts = p.relative_to(path).parts[:-1]
                skip = any(d.startswith(".") or d in _SKIP_DIRS for d in parts)
                if not skip and not excluded(p):
                    yield p
        elif not excluded(path):
            yield path


def _parser() -> argparse.ArgumentParser:
    rules = "\n".join(f"  {r.code}  {r.summary}" for r in RULES)
    parser = argparse.ArgumentParser(
        prog="desphinx",
        description="Find reStructuredText and Sphinx markup in Python docstrings "
        "and comments.",
        epilog=f"rules:\n{rules}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path()],
        help="files or directories to check (default: the current directory)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="rewrite the markup that has one Markdown equivalent",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="skip files whose path matches GLOB; may be repeated",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line interface.

    Args:
        argv: Arguments, excluding the program name. Defaults to `sys.argv`.

    Returns:
        The exit status: 0 if nothing was found or fixed, otherwise 1.
    """
    args = _parser().parse_args(argv)
    failed = False
    for path in _python_files(args.paths, args.exclude):
        source = path.read_text(encoding="utf-8")
        try:
            if args.fix and (fixed := fix(source)) != source:
                path.write_text(fixed, encoding="utf-8")
                print(f"{path}: fixed")
                source = fixed
                failed = True
            findings = check(source)
        except SyntaxError as e:
            print(f"{path}: skipped, not valid Python ({e.msg})", file=sys.stderr)
            continue
        for finding in findings:
            print(f"{path}:{finding}")
        failed = failed or bool(findings)
    return int(failed)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
