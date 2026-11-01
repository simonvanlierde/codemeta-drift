"""The one parser and resolver for mapping paths in this package.

citesync keeps its own copy of the grammar, checked against ``mapping-vectors.json``.
"""

import re
from typing import Any, NamedTuple

from codemeta_drift.export import PATH

# One step of the schema's path pattern: a key, then optionally ``[]`` or ``[k=v]``.
STEP = re.compile(
    r"(?P<key>@?[A-Za-z_][A-Za-z0-9_@-]*)(?P<list>\[(?:(?P<fkey>@?[A-Za-z_][A-Za-z0-9_@-]*)=(?P<fvalue>[A-Za-z0-9_.-]+))?\])?"
)


class Step(NamedTuple):
    """One step: a key, and whether and how it selects list elements."""

    key: str
    is_list: bool  # true for ``[]`` and for ``[k=v]``, which also walks a list
    filter_key: str | None
    filter_value: str | None


def parse(path: str) -> list[list[Step]]:
    """The alternatives of ``path``, each a list of steps. Raises ValueError when it is not in the grammar."""
    if not PATH.fullmatch(path):
        msg = f"not a mapping path: {path!r}"
        raise ValueError(msg)
    return [
        [Step(m["key"], m["list"] is not None, m["fkey"], m["fvalue"]) for m in STEP.finditer(alternative)]
        for alternative in path.split(" | ")
    ]


def resolve(document: Any, path: str) -> list[Any]:  # noqa: ANN401 - parsed JSON
    """The values ``path`` names in ``document``, in document order, from the first alternative that has any."""
    for steps in parse(path):
        nodes = [document]
        for step in steps:
            nodes = [n[step.key] for n in nodes if isinstance(n, dict) and step.key in n]
            if step.is_list:
                nodes = [e for n in nodes if isinstance(n, list) for e in n]
            if step.filter_key:
                nodes = [e for e in nodes if isinstance(e, dict) and str(e.get(step.filter_key)) == step.filter_value]
        if nodes:
            return nodes
    return []
