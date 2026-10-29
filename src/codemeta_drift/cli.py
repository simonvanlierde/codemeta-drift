"""Command line: ``codemeta-drift <checkout> [--ref REF] [--json]``.

Exit status 0 means no drift, 1 means at least one finding (SKIPPED ones do
not count), 2 means bad arguments, an unreadable or malformed checkout, or one
without the context and the property table.

``codemeta-drift export [checkout] --tag TAG [--ref REF] [--out FILE] [--schemas DIR]``
writes the mapping export. It exits 0 when written, 1 when a crosswalk cell has
no path and no curated row (or a path is not in its format's schema), and 2 as above.
"""

import argparse
import fnmatch
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from codemeta_drift.checks import CONTEXT, TABLE, check
from codemeta_drift.conformance import SCHEMA_FILES, conform
from codemeta_drift.export import curated_tags, export

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

    def git(*args: str, stdin: bytes = b"") -> bytes:
        return subprocess.run(["git", "-C", str(root), *args], input=stdin, check=True, capture_output=True).stdout

    commit = git("rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}").strip().decode()

    # Each entry is "<mode> <type> <object>\t<path>". -z keeps git from quoting
    # non-ASCII names, which would then not match INPUTS.
    blobs = {}
    for entry in git("ls-tree", "-r", "-z", commit).decode("utf-8").split("\0"):
        if entry:
            meta, path = entry.split("\t", 1)
            _, kind, oid = meta.split()
            if kind == "blob" and is_input(path):
                blobs[path] = oid

    # One cat-file process reads every file; one git process per file doubles the run time.
    # Its output is "<object> blob <size>\n<content>\n" per file, in the order asked.
    out = git("cat-file", "--batch", stdin="".join(f"{oid}\n" for oid in blobs.values()).encode())
    files, pos = {}, 0
    for path in blobs:
        header_end = out.index(b"\n", pos)
        start = header_end + 1
        end = start + int(out[pos:header_end].split()[2])
        files[path] = out[start:end].decode("utf-8")
        pos = end + 1
    return files


def export_main(argv: list[str]) -> int:
    """Write the mapping export for one CodeMeta tag, or list the cells that block it."""
    parser = argparse.ArgumentParser(prog="codemeta-drift export", description="Write a mapping export.")
    parser.add_argument("checkout", type=Path, nargs="?", default=Path(), help="root of a codemeta clone (default: .)")
    parser.add_argument("--tag", required=True, help="the CodeMeta release; picks the curated rows")
    parser.add_argument("--ref", help="read this commit, tag or branch instead of the working tree")
    parser.add_argument("--out", type=Path, help="write here instead of standard output")
    parser.add_argument("--schemas", type=Path, help="check every path against the format schemas in this directory")
    args = parser.parse_args(argv)

    if args.tag not in curated_tags():
        print(f"codemeta-drift: no curated rows for {args.tag}; have {', '.join(curated_tags())}", file=sys.stderr)
        return 2
    try:
        files = read_ref(args.checkout, args.ref) if args.ref else read_dir(args.checkout)
        if TABLE not in files:
            print(f"codemeta-drift: {args.checkout} has no {TABLE}", file=sys.stderr)
            return 2
        mapping, findings = export(files, args.tag)
        if args.schemas:
            schemas = {f: json.loads((args.schemas / name).read_text("utf-8")) for f, name in SCHEMA_FILES.items()}
            findings += conform(mapping["rows"], schemas)
    except subprocess.CalledProcessError as err:
        print(f"codemeta-drift: cannot read {args.checkout}: {err.stderr.decode().strip()}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError) as err:
        print(f"codemeta-drift: cannot read {args.checkout}: {type(err).__name__}: {err}", file=sys.stderr)
        return 2
    if findings:
        print("\n".join(map(str, findings)))
        return 1
    text = json.dumps(mapping, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run every check on one snapshot and print the findings, or run a subcommand."""
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["export"]:
        return export_main(argv[1:])
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
        print(f"codemeta-drift: cannot read {args.checkout}: {err.stderr.decode().strip()}", file=sys.stderr)
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
