"""Command line: ``codemeta-drift <checkout> [--ref REF] [--json]``.

Every command exits 0 when done, 1 on findings (SKIPPED ones do not count), 2 on a usage
error, 3 when it could not run (an unreadable or malformed checkout, one without the context
and the property table, a file that can't be read or written) and 130 when interrupted.

``codemeta-drift export [checkout] --tag TAG [--out FILE] [--schemas DIR]`` writes the
mapping export from the commit of tag TAG, never the working tree, since every row says
it was read from that tag. Its findings are rows it can't make (such as a crosswalk cell
with no path and no curated row, or a path not in its format's schema), printed on standard
error so standard output is never a partial file. A TAG with no curated rows is a usage error.
"""

import argparse
import contextlib
import fnmatch
import json
import os
import signal
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any, NoReturn

from codemeta_drift.checks import CONTEXT, TABLE, check
from codemeta_drift.conformance import SCHEMA_FILES, conform
from codemeta_drift.export import curated_tags, export, formats, generator

JSON_VERSION = 1
"""Every ``--json`` report's ``schema_version``: a release may add keys; removing or retyping one bumps it."""

EXIT_FINDINGS, EXIT_USAGE, EXIT_CANNOT_RUN, EXIT_INTERRUPTED = 1, 2, 3, 130

READ_ERRORS = (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError, RecursionError)
"""What a missing, unreadable or malformed input raises: the command could not run (exit 3), never exit 1."""

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


def json_report(fields: Mapping[str, object], errors: Sequence[dict[str, str | None]] = ()) -> str:
    """A ``--json`` report: ``schema_version``, the command's fields, and ``errors`` as {message, help} objects."""
    return (
        json.dumps({"schema_version": JSON_VERSION, **fields, "errors": list(errors)}, indent=2, ensure_ascii=False)
        + "\n"
    )


EXIT_CODES = "exit codes: 0 done, 1 findings, 2 usage error, 3 could not run, 130 interrupted"

EXAMPLES = {
    "check": "codemeta-drift ../codemeta --json",
    "export": "codemeta-drift export ../codemeta --tag 4.0 --out mapping-4.0.json",
    "watch": (
        "codemeta-drift watch ../codemeta --tag 4.0 --before old --after new "
        "--citesync-source MAPPING_SOURCE --latest v0.8.0 --existing issue-titles.json"
    ),
    "pair": "codemeta-drift hub pair mapping-4.0.json --from pep621 --to cargo",
    "sssom": "codemeta-drift hub sssom mapping-4.0.json --out spokes.sssom.tsv",
    "crosswalk": "codemeta-drift hub crosswalk mapping-4.0.json ../codemeta --format cargo",
    "coverage": "codemeta-drift hub coverage mapping-4.0.json --codemeta ../codemeta --json",
}
"""One example per command, shown in its ``--help``."""


def command_parser(name: str, prog: str, description: str, **kwargs: Any) -> argparse.ArgumentParser:  # noqa: ANN401 - argparse's own
    """A parser whose help ends with the command's example and the exit codes."""
    return argparse.ArgumentParser(
        prog=prog,
        description=description,
        epilog=f"example:\n  {EXAMPLES[name]}\n\n{EXIT_CODES}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        **kwargs,
    )


def read_text(path: Path) -> str:
    """A file's text, or standard input for ``-``."""
    return sys.stdin.read() if str(path) == "-" else path.read_text("utf-8")


def report_out(report: str, out: Path | None) -> None:
    """Write a ``--json`` report to ``out``, or to standard output without one or when it can't be written."""
    if out:
        with contextlib.suppress(OSError):
            out.write_text(report, encoding="utf-8")
            return
    print(report, end="")


def fail(code: int, message: str, *, as_json: bool, out: Path | None = None) -> int:
    """Report why a command could not run or was misused, as a JSON error or a line on standard error."""
    if as_json:
        report_out(json_report({}, [{"message": message, "help": None}]), out)
    else:
        print(f"codemeta-drift: {message}", file=sys.stderr)
    return code


def found(findings: Sequence[object], *, as_json: bool, out: Path | None = None, **empty: object) -> int:
    """Report the rows a command can't make; ``empty`` is what the JSON report holds besides ``findings``."""
    if as_json:
        report_out(json_report({**empty, "findings": [str(f) for f in findings]}), out)
    else:
        print("\n".join(map(str, findings)), file=sys.stderr)
    return EXIT_FINDINGS


def is_input(path: str) -> bool:
    """Whether a repository-relative path matches INPUTS, with ``*`` stopping at ``/`` as in Path.glob."""
    return any(fnmatch.fnmatchcase(path, g) and path.count("/") == g.count("/") for g in INPUTS)


def read_dir(root: Path) -> dict[str, str]:
    """The input files of a working tree, as path -> text."""

    def linked(path: Path) -> bool:  # the file or a folder on its way: read_ref reads no link, so neither does this
        relative = path.relative_to(root)
        return any((root / part).is_symlink() for part in [relative, *relative.parents[:-1]])

    return {
        p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
        for g in INPUTS
        for p in root.glob(g)
        if p.is_file() and not linked(p)
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
            mode, kind, oid = meta.split()
            if kind == "blob" and mode != "120000" and is_input(path):  # 120000: a symlink's target text
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
    parser = command_parser("export", "codemeta-drift export", "Write a mapping export.")
    parser.add_argument("checkout", type=Path, nargs="?", default=Path(), help="root of a codemeta clone (default: .)")
    parser.add_argument("--tag", required=True, help="the CodeMeta release tag to read; picks the curated rows")
    parser.add_argument("--out", type=Path, help="write here instead of standard output")
    parser.add_argument("--schemas", type=Path, help="check every path against the format schemas in this directory")
    parser.add_argument("--json", action="store_true", help="write a JSON report (mapping, findings, errors)")
    args = parser.parse_args(argv)
    kind = {"as_json": args.json, "out": args.out}

    if args.tag not in curated_tags():
        return fail(EXIT_USAGE, f"no curated rows for {args.tag}; have {', '.join(curated_tags())}", **kind)
    # Each step names what it failed on: the checkout, a schema file or the output file.
    target: object = f"{args.checkout} at tag {args.tag}"
    try:
        files = read_ref(args.checkout, f"refs/tags/{args.tag}")
        if missing := [p for p in (CONTEXT, TABLE) if p not in files]:
            return fail(EXIT_CANNOT_RUN, f"{target} has no {' or '.join(missing)}", **kind)
        mapping, findings = export(files, args.tag)
        if args.schemas:
            schemas = {}
            for fmt, name in SCHEMA_FILES.items():
                target = args.schemas / name
                schemas[fmt] = json.loads(target.read_text("utf-8"))
            findings += conform(mapping["rows"], schemas)
        if findings:
            return found(findings, mapping=None, **kind)
        text = (
            json_report({"mapping": mapping, "findings": []})
            if args.json
            else json.dumps(mapping, indent=2, ensure_ascii=False) + "\n"
        )
        if args.out:
            target = args.out
            args.out.write_text(text, encoding="utf-8")
    except subprocess.CalledProcessError as err:
        return fail(EXIT_CANNOT_RUN, f"cannot read {target}: {err.stderr.decode().strip()}", **kind)
    except READ_ERRORS as err:
        return fail(EXIT_CANNOT_RUN, f"cannot read or write {target}: {type(err).__name__}: {err}", **kind)
    # Outside the try, as in every subcommand: a stdout that fails is entry()'s to report, quietly for a closed pipe.
    if not args.out:
        print(text, end="")
    return 0


def coverage_text(mapping: dict, checkout: Path | None, *, as_json: bool) -> str:
    """``hub coverage`` output; a CodeMeta checkout adds the crosswalks nobody reviewed, read at the export's tag."""
    from codemeta_drift.coverage import coverage, markdown, unreviewed  # noqa: PLC0415 - only the hub command needs this
    from codemeta_drift.hub import validate_mapping  # noqa: PLC0415 - only the hub command needs this

    validate_mapping(mapping)  # before git sees its codemeta_tag
    try:
        files = read_ref(checkout, mapping["codemeta_tag"]) if checkout else None
    except subprocess.CalledProcessError as err:
        msg = f"cannot read {checkout}: {err.stderr.decode().strip()}"
        raise ValueError(msg) from err
    if not as_json:
        return markdown(mapping, files)
    data = coverage(mapping) | ({"unreviewed": unreviewed(files, mapping)} if files is not None else {})
    return json_report(data)


def hub_parser() -> argparse.ArgumentParser:
    """The ``hub`` command's options."""
    ids = sorted({*(fmt for tag in curated_tags() for fmt in formats(tag)), "gomod"})
    parser = argparse.ArgumentParser(
        prog="codemeta-drift hub",
        description="Join curated field correspondences.",
        epilog=f"formats for --format, --from and --to: {', '.join(ids)}\n\n{EXIT_CODES}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("pair", "sssom", "crosswalk", "coverage"):
        command = commands.add_parser(
            name,
            epilog=f"example:\n  {EXAMPLES[name]}\n\n{EXIT_CODES}",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        command.add_argument("mapping", type=Path, help="a mapping JSON export, or - for standard input")
        command.add_argument("--out", type=Path, help="write here instead of standard output")
        if name == "crosswalk":
            command.add_argument("checkout", type=Path, help="checkout with the property table to preserve")
            command.add_argument(
                "--format", required=True, help="format id for the crosswalk column", choices=ids, metavar="FORMAT"
            )
        if name == "coverage":
            command.add_argument("--json", action="store_true", help="write the cells as JSON instead of Markdown")
        else:
            command.add_argument("--json", action="store_true", help="write a JSON report instead of the text output")
        if name == "coverage":
            command.add_argument(
                "--codemeta", type=Path, help="CodeMeta checkout: also list the crosswalks nobody has reviewed"
            )
        if name == "pair":
            command.add_argument(
                "--from", dest="source", required=True, help="source format id", choices=ids, metavar="FORMAT"
            )
            command.add_argument(
                "--to", dest="target", required=True, help="target format id", choices=ids, metavar="FORMAT"
            )
    return parser


def hub_main(argv: list[str]) -> int:
    """Write SSSOM spokes or field correspondences between two formats."""
    from codemeta_drift.hub import UsageError, crosswalk, pair_rows, sssom, table  # noqa: PLC0415 - only hub needs this

    args = hub_parser().parse_args(argv)
    try:
        mapping = json.loads(read_text(args.mapping))
        rows = None
        if args.command == "crosswalk":
            text = crosswalk(mapping, {TABLE: (args.checkout / TABLE).read_text("utf-8")}, args.format)
        elif args.command == "coverage":
            text = coverage_text(mapping, args.codemeta, as_json=args.json)
        elif args.command == "sssom":
            text = sssom(mapping)
        else:
            rows = pair_rows(mapping, args.source, args.target)
            text = table(rows, ["term", "source", "target"])
        if args.json and args.command != "coverage":
            text = json_report({"rows": rows} if rows is not None else {"text": text})
        if args.out:
            args.out.write_text(text, encoding="utf-8")
            return 0
    except UsageError as err:
        return fail(EXIT_USAGE, str(err), as_json=args.json, out=args.out)
    except (OSError, ValueError, RecursionError) as err:
        return fail(EXIT_CANNOT_RUN, str(err), as_json=args.json, out=args.out)
    print(text, end="")  # outside the try, as in export_main
    return 0


def watch_main(argv: list[str]) -> int:
    """Compare downloaded schemas and print issue drafts, without opening issues."""
    from codemeta_drift.watcher import issue_plans, pin_tag, schema_changes  # noqa: PLC0415 - only watch needs this

    parser = command_parser("watch", "codemeta-drift watch", "Preview schema and pin issues offline, as a JSON report.")
    parser.add_argument("checkout", type=Path)
    parser.add_argument("--tag", required=True, help="CodeMeta tag used for the curated export")
    parser.add_argument("--before", required=True, type=Path, help="previous schema directory")
    parser.add_argument("--after", required=True, type=Path, help="new schema directory")
    parser.add_argument("--citesync-source", required=True, type=Path, help="citesync's MAPPING_SOURCE file")
    parser.add_argument("--latest", required=True, help="latest stable codemeta-drift release tag")
    parser.add_argument(
        "--existing",
        required=True,
        type=Path,
        help="JSON list of all issue titles, including closed issues; - for standard input",
    )
    args = parser.parse_args(argv)
    # The output is a JSON report whatever happens, so an error is one too.
    if args.tag not in curated_tags():
        return fail(EXIT_USAGE, f"no curated rows for {args.tag}; have {', '.join(curated_tags())}", as_json=True)
    try:
        mapping, findings = export(read_ref(args.checkout, f"refs/tags/{args.tag}"), args.tag)
        if findings:
            return found(findings, as_json=True, issues=[])
        snapshots = [
            {fmt: json.loads((directory / name).read_text("utf-8")) for fmt, name in SCHEMA_FILES.items()}
            for directory in (args.before, args.after)
        ]
        pin = pin_tag(args.citesync_source.read_text("utf-8"))
        existing = json.loads(read_text(args.existing))
        if not isinstance(existing, list) or any(not isinstance(title, str) for title in existing):
            msg = "existing issues must be a JSON list of titles"
            raise ValueError(msg)
        plans = issue_plans(schema_changes(mapping["rows"], *snapshots), pin, args.latest, set(existing))
    except subprocess.CalledProcessError as err:
        return fail(EXIT_CANNOT_RUN, err.stderr.decode().strip(), as_json=True)
    except READ_ERRORS as err:
        return fail(EXIT_CANNOT_RUN, f"{type(err).__name__}: {err}", as_json=True)
    print(json_report({"issues": plans, "findings": []}), end="")  # outside the try, as in export_main
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run every check on one snapshot and print the findings, or run a subcommand."""
    argv = sys.argv[1:] if argv is None else argv
    commands = {"hub": hub_main, "watch": watch_main, "export": export_main}
    try:
        if argv and argv[0] in commands:
            return commands[argv[0]](argv[1:])
        return check_main(argv)
    except KeyboardInterrupt:
        with contextlib.suppress(OSError):  # an unwritable stderr must not turn Ctrl-C into exit 3
            print("codemeta-drift: interrupted", file=sys.stderr)
        return EXIT_INTERRUPTED


class VersionAction(argparse.Action):
    """``--version``, reading the installed version only when asked: importlib.metadata costs about 10 ms."""

    def __init__(self, option_strings: Sequence[str], dest: str, **kwargs: Any) -> None:  # noqa: ANN401 - argparse's own
        super().__init__(option_strings, dest, nargs=0, help="show the version and exit", **kwargs)

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,  # noqa: ARG002 - argparse's signature
        values: str | Sequence[Any] | None,  # noqa: ARG002
        option_string: str | None = None,  # noqa: ARG002
    ) -> None:
        """Print ``codemeta-drift <version>`` and exit 0."""
        print(f"{parser.prog} {generator()['version']}")
        parser.exit()


def check_main(argv: list[str]) -> int:
    """Run every check on one snapshot and print the findings."""
    parser = command_parser("check", "codemeta-drift", "Report where CodeMeta's files disagree.")
    parser.epilog = (
        f"{parser.epilog}\n\n"
        "codemeta-drift export --help for mapping JSON\n"
        "codemeta-drift hub --help for crosswalks and SSSOM\n"
        "codemeta-drift watch --help for schema comparison"
    )
    parser.add_argument("--version", action=VersionAction)
    parser.add_argument("checkout", type=Path, help="root of a codemeta clone")
    parser.add_argument("--ref", help="read this commit, tag or branch instead of the working tree")
    parser.add_argument("--json", action="store_true", help="print the findings as one JSON document")
    args = parser.parse_args(argv)

    def cannot_run(message: str, help_: str | None) -> int:
        # A malformed file must not exit 1, which means drift.
        if args.json:
            print(json_report({"tool": generator(), "findings": []}, [{"message": message, "help": help_}]), end="")
        else:
            print(f"codemeta-drift: {message}", file=sys.stderr)
        return EXIT_CANNOT_RUN

    try:
        files = read_ref(args.checkout, args.ref) if args.ref else read_dir(args.checkout)
        if missing := [p for p in (CONTEXT, TABLE) if p not in files]:
            return cannot_run(f"{args.checkout} has no {' or '.join(missing)}", "pass the root of a codemeta clone")
        findings = check(files)
    except subprocess.CalledProcessError as err:
        return cannot_run(f"cannot read {args.checkout}: {err.stderr.decode().strip()}", None)
    except READ_ERRORS as err:
        return cannot_run(f"cannot read {args.checkout}: {type(err).__name__}: {err}", None)
    if args.json:
        print(json_report({"tool": generator(), "findings": [asdict(f) for f in findings]}), end="")
    elif findings:
        print("\n".join(map(str, findings)))
    return EXIT_FINDINGS if any(f.code != "SKIPPED" for f in findings) else 0


def entry() -> NoReturn:
    """The ``codemeta-drift`` command: run ``main``, and after Ctrl-C die of SIGINT, as the shell expects.

    A shell loop stops on Ctrl-C only when the command was killed by the signal; exit code 130 alone
    does not stop it. ``main`` itself returns 130, for callers that run it in-process.
    """
    # A closed fd 2 makes sys.stderr None, and print(file=None) writes to stdout: messages would land in the output.
    if sys.stderr is None:
        sys.stderr = Path(os.devnull).open("w", encoding="utf-8")  # noqa: SIM115 - lives until exit
    code = EXIT_CANNOT_RUN
    try:
        try:
            code = main()
        except SystemExit as done:  # argparse's --help, --version and usage errors still have output to flush
            if not isinstance(done.code, int | None):
                raise
            code = done.code or 0
        if sys.stdout is not None:  # None when the caller closed fd 1
            sys.stdout.flush()
        sys.stderr.flush()  # a usage error's message is output too
    except OSError as err:  # a full disk or a closed pipe; Python itself would exit 120 or 1
        if not isinstance(err, BrokenPipeError):  # a reader that stops early, as head does, is no news
            with contextlib.suppress(OSError):
                print(f"codemeta-drift: cannot write the output: {err}", file=sys.stderr)
        # Point the streams at devnull, or the interpreter's exit flush fails again and exits 120.
        devnull = os.open(os.devnull, os.O_WRONLY)
        for stream in (sys.stdout, sys.stderr):
            with contextlib.suppress(OSError, ValueError, AttributeError):
                os.dup2(devnull, stream.fileno())
        if code != EXIT_INTERRUPTED:
            sys.exit(EXIT_CANNOT_RUN)
    if code == EXIT_INTERRUPTED and sys.platform != "win32":
        with contextlib.suppress(OSError):
            sys.stderr.flush()
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        os.kill(os.getpid(), signal.SIGINT)
    sys.exit(code)


if __name__ == "__main__":
    entry()
