"""Command line: ``codemeta-drift <checkout> [--ref REF] [--json]``.

Exit status 0 means no drift, 1 means at least one finding (SKIPPED ones do
not count), 2 means bad arguments, an unreadable or malformed checkout, or one
without the context and the property table.

``codemeta-drift export [checkout] --tag TAG [--out FILE] [--schemas DIR]`` writes the
mapping export from the commit of tag TAG, never the working tree, since every row says
it was read from that tag. It exits 0 when written, 1 when a row can't be made (such as a
crosswalk cell with no path and no curated row, or a path not in its format's schema), with
the findings on standard error so standard output is never a partial file, and 2 as above,
or when the checkout has no tag TAG or a file can't be read or written.
"""

import argparse
import fnmatch
import json
import subprocess
import sys
from dataclasses import asdict
from importlib import metadata
from pathlib import Path

from codemeta_drift.checks import CONTEXT, TABLE, check
from codemeta_drift.conformance import SCHEMA_FILES, conform
from codemeta_drift.export import curated_tags, export

JSON_VERSION = 1
"""The ``--json`` document's version: a minor release may add keys; removing or retyping one bumps it."""

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
    return {
        p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
        for g in INPUTS
        for p in root.glob(g)
        if p.is_file()  # as read_ref, which reads only blobs
    }


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
    parser.add_argument("--tag", required=True, help="the CodeMeta release tag to read; picks the curated rows")
    parser.add_argument("--out", type=Path, help="write here instead of standard output")
    parser.add_argument("--schemas", type=Path, help="check every path against the format schemas in this directory")
    args = parser.parse_args(argv)

    if args.tag not in curated_tags():
        print(f"codemeta-drift: no curated rows for {args.tag}; have {', '.join(curated_tags())}", file=sys.stderr)
        return 2
    # Each step names what it failed on: the checkout, a schema file or the output file.
    target: object = f"{args.checkout} at tag {args.tag}"
    try:
        files = read_ref(args.checkout, f"refs/tags/{args.tag}")
        if TABLE not in files:
            print(f"codemeta-drift: {target} has no {TABLE}", file=sys.stderr)
            return 2
        mapping, findings = export(files, args.tag)
        if args.schemas:
            schemas = {}
            for fmt, name in SCHEMA_FILES.items():
                target = args.schemas / name
                schemas[fmt] = json.loads(target.read_text("utf-8"))
            findings += conform(mapping["rows"], schemas)
        if findings:
            print("\n".join(map(str, findings)), file=sys.stderr)
            return 1
        text = json.dumps(mapping, indent=2, ensure_ascii=False) + "\n"
        if args.out:
            target = args.out
            args.out.write_text(text, encoding="utf-8")
        else:
            print(text, end="")
    except subprocess.CalledProcessError as err:
        print(f"codemeta-drift: cannot read {target}: {err.stderr.decode().strip()}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError) as err:
        print(f"codemeta-drift: cannot read or write {target}: {type(err).__name__}: {err}", file=sys.stderr)
        return 2
    return 0


def hub_main(argv: list[str]) -> int:
    """Write SSSOM spokes or field correspondences between two formats."""
    from codemeta_drift.coverage import coverage, markdown  # noqa: PLC0415 - only the hub command needs this
    from codemeta_drift.hub import crosswalk, pair_rows, sssom, table  # noqa: PLC0415 - only the hub command needs this

    parser = argparse.ArgumentParser(prog="codemeta-drift hub", description="Join curated field correspondences.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("pair", "sssom", "crosswalk", "coverage"):
        command = commands.add_parser(name)
        command.add_argument("mapping", type=Path, help="a mapping JSON export")
        command.add_argument("--out", type=Path, help="write here instead of standard output")
        if name == "crosswalk":
            command.add_argument("checkout", type=Path, help="checkout with the property table to preserve")
            command.add_argument("--format", required=True, help="format id for the crosswalk column")
        if name == "coverage":
            command.add_argument("--json", action="store_true", help="write the cells as JSON instead of Markdown")
        if name == "pair":
            command.add_argument("--from", dest="source", required=True, help="source format id")
            command.add_argument("--to", dest="target", required=True, help="target format id")
    args = parser.parse_args(argv)
    try:
        mapping = json.loads(args.mapping.read_text("utf-8"))
        if args.command == "crosswalk":
            text = crosswalk(mapping, {TABLE: (args.checkout / TABLE).read_text("utf-8")}, args.format)
        elif args.command == "coverage":
            text = (
                json.dumps(coverage(mapping), indent=2, ensure_ascii=False) + "\n" if args.json else markdown(mapping)
            )
        elif args.command == "sssom":
            text = sssom(mapping)
        else:
            text = table(pair_rows(mapping, args.source, args.target), ["term", "source", "target"])
        if args.out:
            args.out.write_text(text, encoding="utf-8")
        else:
            print(text, end="")
    except (OSError, ValueError) as err:
        print(f"codemeta-drift: {err}", file=sys.stderr)
        return 2
    return 0


def watch_main(argv: list[str]) -> int:
    """Compare downloaded schemas and print issue drafts, without opening issues."""
    from codemeta_drift.watcher import issue_plans, schema_changes  # noqa: PLC0415 - only watch needs this

    parser = argparse.ArgumentParser(prog="codemeta-drift watch", description="Preview schema and pin issues offline.")
    parser.add_argument("checkout", type=Path)
    parser.add_argument("--tag", required=True, help="CodeMeta tag used for the curated export")
    parser.add_argument("--before", required=True, type=Path, help="previous schema directory")
    parser.add_argument("--after", required=True, type=Path, help="new schema directory")
    parser.add_argument("--citesync-source", required=True, type=Path, help="citesync's MAPPING_SOURCE file")
    parser.add_argument("--latest", required=True, help="latest stable codemeta-drift release tag")
    parser.add_argument(
        "--existing", required=True, type=Path, help="JSON list of all issue titles, including closed issues"
    )
    args = parser.parse_args(argv)
    try:
        mapping, findings = export(read_ref(args.checkout, f"refs/tags/{args.tag}"), args.tag)
        if findings:
            print("\n".join(map(str, findings)), file=sys.stderr)
            return 1
        snapshots = [
            {fmt: json.loads((directory / name).read_text("utf-8")) for fmt, name in SCHEMA_FILES.items()}
            for directory in (args.before, args.after)
        ]
        pins = [
            line.split()[1] for line in args.citesync_source.read_text("utf-8").splitlines() if line.startswith("tag ")
        ]
        if len(pins) != 1:
            msg = "MAPPING_SOURCE must contain exactly one tag line"
            raise ValueError(msg)  # noqa: TRY301 - report malformed input with read errors
        existing = json.loads(args.existing.read_text("utf-8"))
        if not isinstance(existing, list) or any(not isinstance(title, str) for title in existing):
            msg = "existing issues must be a JSON list of titles"
            raise ValueError(msg)  # noqa: TRY301 - report malformed input with read errors
        changes = schema_changes(mapping["rows"], *snapshots)
        print(json.dumps(issue_plans(changes, pins[0], args.latest, set(existing)), indent=2))
    except subprocess.CalledProcessError as err:
        print(f"codemeta-drift: {err.stderr.decode().strip()}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError) as err:
        print(f"codemeta-drift: {type(err).__name__}: {err}", file=sys.stderr)
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run every check on one snapshot and print the findings, or run a subcommand."""
    argv = sys.argv[1:] if argv is None else argv
    commands = {"hub": hub_main, "watch": watch_main, "export": export_main}
    if argv and argv[0] in commands:
        return commands[argv[0]](argv[1:])
    parser = argparse.ArgumentParser(
        prog="codemeta-drift",
        description="Report where CodeMeta's files disagree.",
        epilog=(
            "codemeta-drift export --help for mapping JSON; "
            "codemeta-drift hub --help for crosswalks and SSSOM; "
            "codemeta-drift watch --help for schema comparison."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {metadata.version('codemeta-drift')}")
    parser.add_argument("checkout", type=Path, help="root of a codemeta clone")
    parser.add_argument("--ref", help="read this commit, tag or branch instead of the working tree")
    parser.add_argument("--json", action="store_true", help="print the findings as one JSON document")
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
        tool = {"name": "codemeta-drift", "version": metadata.version("codemeta-drift")}
        print(json.dumps({"version": JSON_VERSION, "tool": tool, "findings": [asdict(f) for f in findings]}, indent=2))
    else:
        print("\n".join(map(str, findings)))
    return 1 if any(f.code != "SKIPPED" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
