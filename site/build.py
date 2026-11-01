"""Build the coverage web page into a directory: the static files, data.json and the SSSOM spokes.

    uv run site/build.py --out _site [--codemeta CHECKOUT]

With ``--codemeta``, data.json also holds that checkout's HEAD: its drift findings and the
crosswalk cells that read differently there than at the export's tag.
"""

# ruff: noqa: INP001

import argparse
import json
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

from codemeta_drift.checks import check
from codemeta_drift.cli import read_ref
from codemeta_drift.coverage import coverage, upstream
from codemeta_drift.hub import sssom

ROOT = Path(__file__).resolve().parent.parent
STATIC = ("index.html", "style.css", "main.mjs", "favicon.svg")


def upstream_data(checkout: Path, mapping: dict[str, Any]) -> dict[str, Any]:
    """HEAD of a CodeMeta clone: commit, date, drift findings and cells changed since the export's tag."""
    commit, date = subprocess.run(  # noqa: S603 - fixed git call, no shell
        ["git", "-C", str(checkout), "log", "-1", "--format=%H %cI"],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    files = read_ref(checkout, commit)
    return {
        "commit": commit,
        "date": date,
        "drift": [asdict(f) for f in check(files) if f.code != "SKIPPED"],
        "cells": upstream(files, mapping),
    }


def main() -> None:
    """Copy the page and write its data."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="output directory, replaced if it exists")
    parser.add_argument("--codemeta", type=Path, help="a CodeMeta clone whose HEAD to compare")
    args = parser.parse_args()
    mapping = json.loads((ROOT / "examples/mapping-3.1.json").read_text("utf-8"))
    data = {
        "coverage": coverage(mapping),
        "upstream": upstream_data(args.codemeta, mapping) if args.codemeta else None,
    }
    # Only a directory this script made, or an empty one, is replaced.
    if args.out.exists() and any(args.out.iterdir()) and not (args.out / "data.json").exists():
        parser.error(f"{args.out} is not empty and has no data.json; refusing to replace it")
    shutil.rmtree(args.out, ignore_errors=True)
    args.out.mkdir(parents=True)
    for name in STATIC:
        shutil.copy(ROOT / "site" / name, args.out / name)
    # The SSSOM export's mapping_set_id points here.
    (args.out / f"spokes-{mapping['codemeta_tag']}.sssom.tsv").write_text(sssom(mapping), encoding="utf-8")
    (args.out / "data.json").write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
