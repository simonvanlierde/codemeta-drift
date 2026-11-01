"""Compare downloaded schemas and prepare deduplicated issue drafts without external writes."""

import hashlib
import json
import re
from typing import Any

from codemeta_drift.conformance import array_items, branches, resolve
from codemeta_drift.paths import parse


def schema_paths(root: dict[str, Any]) -> set[str]:
    """Enumerate declared property paths, following local refs and list items, without recursive loops."""

    def walk(node: object, prefix: str, seen: frozenset[int]) -> set[str]:
        paths = set()
        for branch in branches(root, node):
            if id(branch) in seen:
                continue
            visited = seen | {id(branch)}
            properties = branch.get("properties", {})
            if not isinstance(properties, dict):
                msg = "schema properties must be an object"
                raise ValueError(msg)  # noqa: TRY004 - report malformed JSON as one validation error
            for key, child in properties.items():
                path = f"{prefix}.{key}" if prefix else key
                paths.add(path)
                paths |= walk(child, path, visited)
            if prefix:
                for item in array_items(branch):
                    paths |= walk(item, f"{prefix}[]", visited)
        return paths

    return walk(root, "", frozenset())


def schema_changes(rows: list[dict[str, Any]], before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, str]]:
    """List broken mapped paths and newly declared paths without any mapping, in stable order."""
    if before.keys() != after.keys():
        msg = "before and after must contain the same format schemas"
        raise ValueError(msg)
    changes = []
    for fmt, schema in sorted(after.items()):
        if not isinstance(schema, dict) or not isinstance(before[fmt], dict):
            msg = f"{fmt} schema must be an object"
            raise ValueError(msg)  # noqa: TRY004 - report malformed JSON as one validation error
        paths = {
            path
            for row in rows
            if row["format"] == fmt and row["path"] is not None
            for path in row["path"].split(" | ")
        }
        changes.extend(
            {"format": fmt, "kind": "broken", "path": path, "detail": reason}
            for path in sorted(paths)
            if (reason := resolve(schema, path))
        )
        covered = set()
        for path in paths:
            prefix = ""
            for key, is_list, filter_key, _ in parse(path)[0]:
                field = f"{prefix}.{key}" if prefix else key
                covered.add(field)
                if filter_key:
                    covered.add(f"{field}[].{filter_key}")
                prefix = field + ("[]" if is_list else "")
        changes.extend(
            {"format": fmt, "kind": "unmapped", "path": path, "detail": "new field has no mapping row"}
            for path in sorted(schema_paths(schema) - schema_paths(before[fmt]) - covered)
        )
    return changes


def release_version(tag: str) -> tuple[int, int, int]:
    """Numeric stable release version; reject arbitrary refs rather than guessing their order."""
    if not re.fullmatch(r"v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", tag):
        msg = f"expected a stable release tag, got {tag!r}"
        raise ValueError(msg)
    major, minor, patch = map(int, tag.removeprefix("v").split("."))
    return major, minor, patch


def issue_plans(
    changes: list[dict[str, str]], pin_tag: str, latest_tag: str, existing_titles: set[str]
) -> list[dict[str, str]]:
    """Prepare one schema issue and one behind-pin issue, suppressing existing titles.

    Existing titles must include closed issues too: closing an issue is a human decision, and
    an unchanged next run must not reopen it. This function sends nothing and mutates no state.
    """
    plans = []
    if changes:
        digest = hashlib.sha256(json.dumps(changes, sort_keys=True).encode()).hexdigest()[:12]
        plans.append(
            {
                "repo": "simonvanlierde/codemeta-drift",
                "title": f"Review schema changes {digest}",
                "body": "These schema fields need review:\n\n"
                + "\n".join(f"- {c['format']}: {c['kind']} `{c['path']}` ({c['detail']})" for c in changes),
            }
        )
    if release_version(pin_tag) < release_version(latest_tag):
        plans.append(
            {
                "repo": "simonvanlierde/citesync",
                "title": f"Update mapping pin to {latest_tag}",
                "body": f"The mapping pin is {pin_tag}; the latest stable mapping release is {latest_tag}.\n"
                "Review the export and update MAPPING_SOURCE with its matching files and hashes.",
            }
        )
    return [plan for plan in plans if plan["title"] not in existing_titles]
