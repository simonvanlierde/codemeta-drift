"""Build the coverage web page into a directory: the static files, data.json and the SSSOM spokes.

    uv run site/build.py --out _site [--codemeta CHECKOUT]

data.json is the newest tag's matrix and lists every tag with an export; data-<tag>.json holds each
older tag's matrix. With ``--codemeta``, data.json also holds that checkout's HEAD: its drift
findings and the crosswalk cells that read differently there than at the newest tag. Every
matrix also holds the crosswalks nobody has reviewed, read at its tag, so the clone needs the tags,
and each cell's line in its crosswalk file, so the page can link it.
"""

# ruff: noqa: INP001

import argparse
import hashlib
import json
import shutil
import subprocess
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from codemeta_drift.checks import check
from codemeta_drift.cli import READ_ERRORS, read_ref
from codemeta_drift.coverage import coverage, unreviewed, upstream
from codemeta_drift.export import NO_PROPERTY, TERMS, crosswalk_rows, curated_tags
from codemeta_drift.hub import sssom

ROOT = Path(__file__).resolve().parent.parent
STATIC = ("index.html", "style.css", "main.mjs", "fragment.mjs", "favicon.svg")


def upstream_data(checkout: Path, mapping: dict[str, Any]) -> dict[str, Any]:
    """HEAD of a CodeMeta clone: commit, date, drift findings and cells changed since the export's tag."""
    commit, date = (
        subprocess.run(  # noqa: S603 - fixed git call, no shell
            ["git", "-C", str(checkout), "log", "-1", "--format=%H %cI"],  # noqa: S607
            check=True,
            capture_output=True,
        )
        .stdout.decode()
        .split()
    )
    files = read_ref(checkout, commit)
    return {
        "commit": commit,
        "date": date,
        # The day of the build, which is when main was checked; date is main's last commit.
        "checked": datetime.now(UTC).date().isoformat(),
        "drift": [asdict(f) for f in check(files) if f.code != "SKIPPED"],
        "cells": upstream(files, mapping),
    }


def add_lines(files: dict[str, str], cells: list[dict[str, Any]]) -> None:
    """Sets each cell's line in its crosswalk file; None when the cell can't be joined or has no crosswalk."""
    rows: dict[str, dict[tuple[str, str], tuple[int, str]]] = {}
    for cell in cells:
        path = cell["crosswalk"]
        if path not in files:
            cell["line"] = None
            continue
        if path not in rows:
            rows[path] = crosswalk_rows(files, path)
        cell["line"] = rows[path].get(TERMS.get(cell["term"], ("", "")), (None,))[0]


def matrix(mapping: dict[str, Any], files: dict[str, str] | None) -> dict[str, Any]:
    """One tag's page data; ``files`` is CodeMeta at that tag, or None without a clone."""
    data = coverage(mapping)
    data["schema_version"] = mapping["schema_version"]
    # A term names where a CodeMeta property sits (author.@id is a Person's identifier).
    data["properties"] = {t: " ".join(TERMS[t]) if t in TERMS and t not in NO_PROPERTY else None for t in data["terms"]}
    others = None
    if files is not None:
        others = unreviewed(files, mapping)
        add_lines(files, data["cells"])
        add_lines(files, others["cells"])
    return {
        "coverage": data,
        # The hub's rows have no cells; the page opens a codemeta field id (an SSSOM object id) at its term.
        # Reversed, so a path two rows share (identifier, also swhid's) opens the first row's term.
        "hub": {r["path"]: r["term"] for r in reversed(mapping["rows"]) if r["format"] == "codemeta"},
        "unreviewed": others,
    }


def main() -> None:
    """Copy the page and write its data."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="output directory, replaced if it exists")
    parser.add_argument("--codemeta", type=Path, help="a CodeMeta clone whose HEAD to compare")
    args = parser.parse_args()
    tags = curated_tags()
    mappings = {tag: json.loads((ROOT / f"examples/mapping-{tag}.json").read_text("utf-8")) for tag in tags}

    def tag_matrix(tag: str) -> dict[str, Any]:
        return matrix(mappings[tag], read_ref(args.codemeta, tag) if args.codemeta else None)

    newest = tags[-1]
    # Every file is computed before --out is touched, so a failure leaves the last build in place.
    try:
        head = upstream_data(args.codemeta, mappings[newest]) if args.codemeta else None
        data = {"data.json": {"tags": tags, **tag_matrix(newest), "upstream": head}}
        data |= {f"data-{tag}.json": tag_matrix(tag) for tag in tags[:-1]}
        files = {name: json.dumps(value, indent=1, ensure_ascii=False) + "\n" for name, value in data.items()}
        # The SSSOM export's mapping_set_id points here, for every tag with an export, so an older set's id resolves.
        files |= {f"spokes-{tag}.sssom.tsv": sssom(mappings[tag]) for tag in tags}
    except subprocess.CalledProcessError as err:
        parser.error(
            f"cannot read {args.codemeta}, which needs the tags {', '.join(tags)}: {err.stderr.decode().strip()}"
        )
    except READ_ERRORS as err:
        parser.error(f"cannot read {args.codemeta}: {type(err).__name__}: {err}")
    if args.out.is_symlink():  # rmtree cannot replace a link, and must not empty its target
        parser.error(f"{args.out} is a symbolic link")
    # Only a directory this script made, or an empty one, is replaced.
    if args.out.exists() and not args.out.is_dir():
        parser.error(f"{args.out} is a file, not a directory")
    if args.out.exists() and any(args.out.iterdir()) and not (args.out / "data.json").exists():
        parser.error(f"{args.out} is not empty and has no data.json; refusing to replace it")
    shutil.rmtree(args.out, ignore_errors=True)
    args.out.mkdir(parents=True)
    # data.json first: a write that fails later (a full disk) leaves a directory the next build may replace.
    for name, text in files.items():
        (args.out / name).write_text(text, encoding="utf-8")
    for name in STATIC:
        shutil.copy(ROOT / "site" / name, args.out / name)
    shutil.copytree(ROOT / "site" / "fonts", args.out / "fonts")
    # The docs site's card, which `just og-card` renders.
    shutil.copy(ROOT / "docs/assets/og.png", args.out / "og.png")
    # Pages caches each file for 10 minutes: a module URL that carries its content hash never pairs a fresh page
    # with a stale module. Link previews cache the card by URL, so a redrawn card needs a new one too.
    for page, ref, module in (
        ("main.mjs", '"./{}"', "fragment.mjs"),
        ("index.html", 'src="{}"', "main.mjs"),
        ("index.html", '/{}"', "og.png"),
    ):
        stamp = hashlib.sha256((args.out / module).read_bytes()).hexdigest()[:12]
        text = (args.out / page).read_text("utf-8")
        (args.out / page).write_text(text.replace(ref.format(module), ref.format(f"{module}?v={stamp}")), "utf-8")


if __name__ == "__main__":
    main()
