# Run the full check suite: lint, typecheck, test, docs.
_:
  @just lint typecheck test docs

# Format and lint using ruff and this package's own checker.
[group('check')]
lint:
  ruff format
  desphinx --fix src tests
  ruff check --fix

# Variant of `lint` that doesn't cause any changes to files (for CI).
[group('check')]
lint-check:
  ruff format --check
  desphinx src tests
  ruff check

# Run static type checker.
[group('check')]
typecheck:
  pyright

# Run the test suite using pytest.
[group('test')]
test:
  pytest

# Run tests with coverage report.
[group('test')]
test-cov:
  pytest --cov=desphinx --cov-report=term-missing --cov-fail-under=90

# Run doctest examples embedded in source docstrings.
[group('test')]
doctest:
  pytest --doctest-modules src/desphinx

# Run the example, then build the documentation using Zensical.
[group('docs')]
docs: docs-example
  zensical build

# Run `desphinx --fix` on the example module, writing the fixed module
# and the terminal session to docs/snippets/ for the home page to include.
[group('docs')]
docs-example:
  #!/usr/bin/env bash
  set -euo pipefail
  out="$PWD/docs/snippets"
  tmp=$(mktemp -d)
  trap 'rm -rf "$tmp"' EXIT
  cp "$out/before.py" "$tmp/module.py"
  cd "$tmp"
  status=0
  log=$(desphinx --fix module.py) || status=$?
  printf '$ desphinx --fix module.py\n%s\n$ echo $?\n%s\n' "$log" "$status" \
    > "$out/output.txt"
  cp module.py "$out/after.py"

# Serve the documentation locally with live reload.
[group('docs')]
docs-serve: docs-example
  zensical serve

# Tag the pyproject.toml version and publish it as a GitHub release.
[group('release')]
release:
  #!/usr/bin/env bash
  set -euo pipefail
  v=$(uv version --short)
  [[ $v != *dev* ]] || { echo "refusing to release dev version $v" >&2; exit 1; }
  [[ $(git branch --show-current) == main ]] || { echo "not on main" >&2; exit 1; }
  git diff --quiet HEAD || { echo "uncommitted changes" >&2; exit 1; }
  git fetch --quiet origin main
  [[ $(git rev-parse HEAD) == $(git rev-parse origin/main) ]] \
    || { echo "main differs from origin/main" >&2; exit 1; }
  gh auth status >/dev/null || { echo "gh is not logged in" >&2; exit 1; }
  pre=()
  [[ ! $v =~ (a|b|rc)[0-9]+$ ]] || pre=(--prerelease)
  git tag -a "v$v" -m "v$v"
  git push origin "v$v"
  gh release create "v$v" --verify-tag --generate-notes ${pre[@]+"${pre[@]}"}
