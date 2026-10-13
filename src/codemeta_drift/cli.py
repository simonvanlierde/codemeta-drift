"""Command line: ``codemeta-drift <checkout> [--ref REF] [--json]``.

Exit status 0 means no drift, 1 means at least one finding (SKIPPED ones do
not count), 2 means bad arguments, an unreadable or malformed checkout, or one
without the context and the property table.
"""

import argparse
import fnmatch
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from codemeta_drift.checks import CONTEXT, TABLE, check

INPUTS = (
    "codemeta.jsonld",
    "codemeta_all.jsonld",
    "properties_description.csv",
    "crosswalk.csv",
    "codemeta.json",
    "examples/*.json",
    "crosswalks/*.csv",
)
"""Glob patterns, relative to the repository root, of every file a check reads."""


def is_input(path: str) -> bool:
    """Whether a repository-relative path matches INPUTS, with ``*`` stopping at ``/`` as in Path.glob."""
    return any(fnmatch.fnmatchcase(path, g) and path.count("/") == g.count("/") for g in INPUTS)


def read_dir(root: Path) -> dict[str, str]:
    """The input files of a working tree, as path -> text."""
    return {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8") for g in INPUTS for p in root.glob(g)}


def read_ref(root: Path, ref: str) -> dict[str, str]:
    """The input files at a commit, read with git without touching the working tree."""

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(root), *args], check=True, capture_output=True, text=True, encoding="utf-8"
        ).stdout

    commit = git("rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}").strip()
    # -z: without it git quotes names with non-ASCII characters, and they would not match.
    paths = [p for p in git("ls-tree", "-r", "-z", "--name-only", commit).split("\0") if is_input(p)]
    return {path: git("show", f"{commit}:{path}") for path in paths}


def main(argv: list[str] | None = None) -> int:
    """Run every check on one snapshot and print the findings."""
    parser = argparse.ArgumentParser(prog="codemeta-drift", description="Report where CodeMeta's files disagree.")
    parser.add_argument("checkout", type=Path, help="root of a codemeta clone")
    parser.add_argument("--ref", help="read this commit, tag or branch instead of the working tree")
    parser.add_argument("--json", action="store_true", help="print findings as a JSON array")
    args = parser.parse_args(argv)

    try:
        files = read_ref(args.checkout, args.ref) if args.ref else read_dir(args.checkout)
        if missing := [p for p in (CONTEXT, TABLE) if p not in files]:
            print(f"codemeta-drift: {args.checkout} has no {' or '.join(missing)}", file=sys.stderr)
            return 2
        findings = check(files)
    except subprocess.CalledProcessError as err:
        print(f"codemeta-drift: cannot read {args.checkout}: {err.stderr.strip()}", file=sys.stderr)
        return 2
    # A malformed file must not exit 1, which means drift.
    except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError) as err:
        print(f"codemeta-drift: cannot read {args.checkout}: {type(err).__name__}: {err}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps([asdict(f) for f in findings], indent=2))
    else:
        print("\n".join(map(str, findings)))
    return 1 if any(f.code != "SKIPPED" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
