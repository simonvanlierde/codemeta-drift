"""Demonstrate a synthetic schema rename, deduplicated review and an explicitly approved repair."""

# ruff: noqa: INP001

import argparse
import copy
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from codemeta_drift.conformance import SCHEMA_FILES, conform
from codemeta_drift.watcher import issue_plans, schema_changes

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Write reproducible artifacts; the bundled approval describes a fictional schema change."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path, help="new output directory")
    parser.add_argument("--approval", type=Path, help="reviewed JSON change; without it the pin stays unchanged")
    args = parser.parse_args()
    mapping_bytes = (ROOT / "examples/mapping-3.1.json").read_bytes()
    mapping = json.loads(mapping_bytes)
    contract_bytes = (ROOT / "src/codemeta_drift/mapping.schema.json").read_bytes()
    validator = Draft202012Validator(json.loads(contract_bytes))
    validator.validate(mapping)
    before = {
        fmt: json.loads((ROOT / "tests/fixtures/schemas" / name).read_text("utf-8"))
        for fmt, name in SCHEMA_FILES.items()
    }
    if conform(mapping["rows"], before):
        parser.error("the original mapping does not match its pinned schemas")
    after = copy.deepcopy(before)
    project = after["pep621"]["properties"]["project"]["properties"]
    project["display_name"] = project.pop("name")
    broken = conform(mapping["rows"], after)
    changes = schema_changes(mapping["rows"], before, after)
    drafts = issue_plans(changes, "v0.3.0", "v0.3.0", set())
    repeated = issue_plans(changes, "v0.3.0", "v0.3.0", {draft["title"] for draft in drafts})
    if len(broken) != 1 or len(drafts) != 1 or repeated:
        parser.error("the synthetic rename did not produce one deduplicated review")
    repaired = copy.deepcopy(mapping)
    if args.approval:
        try:
            approval = json.loads(args.approval.read_text("utf-8"))
        except (OSError, ValueError) as err:
            parser.error(f"cannot read approval: {err}")
        expected = {"format": "pep621", "term": "name", "from": "project.name", "to": "project.display_name"}
        if (
            not isinstance(approval, dict)
            or any(approval.get(key) != value for key, value in expected.items())
            or not isinstance(approval.get("reason"), str)
            or not approval["reason"].strip()
        ):
            parser.error("approval does not describe the synthetic rename")
        for row in repaired["rows"]:
            if row["format"] == approval["format"] and row["term"] == approval["term"]:
                row.update(path=approval["to"], source="curated:" + approval["reason"])
        repaired["generator"]["version"] += "+recovery-example"
        validator.validate(repaired)
        if conform(repaired["rows"], after) or schema_changes(repaired["rows"], before, after):
            parser.error("the approved repair still has schema findings")
    result = (json.dumps(repaired, indent=2, ensure_ascii=False) + "\n").encode() if args.approval else mapping_bytes
    pin = {
        "mapping_sha256": hashlib.sha256(result).hexdigest(),
        "schema_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "codemeta_tag": mapping["codemeta_tag"],
        "generator_version": repaired["generator"]["version"],
        "example_only": True,
    }
    # A demonstration never edits the installed mapping or a consumer's real pin.
    try:
        args.out.mkdir(parents=True)
    except OSError as err:
        parser.error(f"cannot create output directory: {err}")
    (args.out / "mapping.json").write_bytes(result)
    (args.out / "pin.json").write_text(json.dumps(pin, indent=2) + "\n", encoding="utf-8")
    (args.out / "drafts.json").write_text(json.dumps(drafts, indent=2) + "\n", encoding="utf-8")
    (args.out / "report.json").write_text(
        json.dumps(
            {"broken": [str(f) for f in broken], "repeated_drafts": repeated, "approved": bool(args.approval)}, indent=2
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
