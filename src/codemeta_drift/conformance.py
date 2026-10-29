"""Check that every path in a mapping export names a property in its format's own JSON Schema.

A step resolves when the schema in reach has the key under ``properties``, a matching
``patternProperties`` entry, or an ``additionalProperties`` schema. Local ``$ref``s are followed,
and a key found in any branch of ``allOf``, ``anyOf`` or ``oneOf`` counts. ``key[]`` and
``key[k=v]`` need the value to be a list (``items``); a filter needs ``k`` in the item schema.
An external ``$ref`` is not followed, so a key only reachable through one does not resolve.
"""

import re
from collections.abc import Iterator, Mapping
from typing import Any

from codemeta_drift.checks import Finding
from codemeta_drift.export import PATH

SCHEMA_FILES = {
    "cff-1.2.0": "cff-1.2.0.json",
    "pep621": "pyproject.json",
    "npm": "package.json",
    "cargo": "cargo.json",
}
"""The schema file for each format that has one. Zenodo and codemeta are not checked."""

STEP = re.compile(r"(?P<key>@?[\w-]+)(?:\[(?:(?P<filter>@?[\w-]+)=[^\]]+)?\])?")

type Schema = dict[str, Any]


def branches(root: Schema, node: object, seen: frozenset[int] = frozenset()) -> Iterator[Schema]:
    """The node and every schema it stands for through local $ref, allOf, anyOf and oneOf."""
    if not isinstance(node, dict) or id(node) in seen:
        return
    seen |= {id(node)}
    yield node
    ref = node.get("$ref")
    if isinstance(ref, str) and ref.startswith("#"):
        target: Any = root
        for part in filter(None, ref[1:].split("/")):
            target = target.get(part.replace("~1", "/").replace("~0", "~"), {}) if isinstance(target, dict) else {}
        yield from branches(root, target, seen)
    for combinator in ("allOf", "anyOf", "oneOf"):
        for sub in node.get(combinator, ()):
            yield from branches(root, sub, seen)


def child(node: Schema, key: str) -> object:
    """The schema of ``key`` inside one object schema, or None when the object has no such key."""
    if key in node.get("properties", {}):
        return node["properties"][key]
    for pattern, sub in node.get("patternProperties", {}).items():
        if re.search(pattern, key):
            return sub
    extra = node.get("additionalProperties")
    return extra if isinstance(extra, dict) else None


def resolve(root: Schema, path: str) -> str | None:
    """Why one path alternative (no `` | ``) is not in the schema, or None when every step resolves."""
    if " | " in path or not PATH.fullmatch(path):
        return "not a path"
    nodes: list[object] = [root]
    for match in STEP.finditer(path):
        key, selector = match["key"], match[0][len(match["key"]) :]
        found = [c for n in nodes for b in branches(root, n) if (c := child(b, key)) is not None]
        if not found:
            return f"no {key!r}"
        if selector:
            found = [b["items"] for n in found for b in branches(root, n) if isinstance(b.get("items"), dict)]
            if not found:
                return f"{key!r} is not a list"
            if (k := match["filter"]) and not any(child(b, k) is not None for n in found for b in branches(root, n)):
                return f"items of {key!r} have no {k!r}"
        nodes = found
    return None


def conform(rows: list[dict[str, Any]], schemas: Mapping[str, Schema]) -> list[Finding]:
    """A ``PATH_NOT_IN_SCHEMA`` finding for each path alternative its format's schema lacks.

    Rows of a format with no entry in ``schemas``, and rows whose path is null, are not checked.
    """
    return [
        Finding("PATH_NOT_IN_SCHEMA", row["format"], row["term"], f"{alternative}: {why}")
        for row in rows
        if (schema := schemas.get(row["format"])) is not None
        for alternative in (row["path"] or "").split(" | ")
        if alternative and (why := resolve(schema, alternative))
    ]
