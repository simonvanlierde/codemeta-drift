"""The one parser and resolver for mapping paths in this package.

citesync keeps its own copy of the grammar, checked against ``mapping-vectors.json``.
"""

import re
from typing import Any, NamedTuple

from codemeta_drift.export import PATH, PIECES

__all__ = ["PIECES", "Step", "parse", "resolve"]

KEY = r"@?[A-Za-z_][A-Za-z0-9_@-]*(?::[A-Za-z_][A-Za-z0-9_-]*)?"
# One step of the schema's path pattern: a key, then optionally ``[]`` or ``[k=v]``.
STEP = re.compile(rf"(?P<key>{KEY})(?P<list>\[(?:(?P<fkey>{KEY})=(?P<fvalue>[A-Za-z0-9_.-]+))?\])?")


class Step(NamedTuple):
    """One step: a key, and whether and how it selects list elements."""

    key: str
    is_list: bool  # true for ``[]`` and for ``[k=v]``, which also walks a list
    filter_key: str | None
    filter_value: str | None


def parse(path: str) -> list[list[list[Step]]]:
    """The alternatives of ``path``, each a list of ``+`` parts, each a list of steps.

    Raises ValueError when ``path`` is not in the grammar.
    """
    if not PATH.fullmatch(path):
        msg = f"not a mapping path: {path!r}"
        raise ValueError(msg)
    return [
        [
            [Step(m["key"], m["list"] is not None, m["fkey"], m["fvalue"]) for m in STEP.finditer(part)]
            for part in alternative.split(" + ")
        ]
        for alternative in path.split(" | ")
    ]


def matches(element: object, key: str, value: str) -> bool:
    """Whether ``element[key]`` is ``value`` as text, or is a list that holds it."""
    if not isinstance(element, dict) or key not in element:
        return False
    found = element[key]
    return any(str(v) == value for v in found) if isinstance(found, list) else str(found) == value


def chain(document: Any, steps: list[Step]) -> list[Any]:  # noqa: ANN401 - parsed JSON
    nodes = [document]
    for step in steps:
        nodes = [n[step.key] for n in nodes if isinstance(n, dict) and step.key in n]
        if step.is_list:
            nodes = [e for n in nodes if isinstance(n, list) for e in n]
        if step.filter_key:
            nodes = [e for e in nodes if matches(e, step.filter_key, step.filter_value or "")]
    return nodes


def resolve(document: Any, path: str) -> list[Any]:  # noqa: ANN401 - parsed JSON
    """The values ``path`` names in ``document``, from the first alternative that has any.

    An alternative's values are its parts' values, part by part, each in document order.
    """
    for parts in parse(path):
        if nodes := [node for steps in parts for node in chain(document, steps)]:
            return nodes
    return []
