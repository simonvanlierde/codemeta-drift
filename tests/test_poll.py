import base64
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.error import HTTPError

import pytest

from codemeta_drift import poll as runner
from codemeta_drift.poll import API, SCHEMA_URLS, fetch_json, poll, publish


def test_poll_uses_current_schemas_and_only_latest_codemeta_tag():
    schema = {"properties": {"title": {"type": "string"}}}
    before = {fmt: {"properties": {"name": {}}} for fmt in (*SCHEMA_URLS, "cff-1.2.0")}
    responses = {
        API + "citation-file-format/citation-file-format/releases/latest": {"tag_name": "1.2.0"},
        API + "simonvanlierde/codemeta-drift/releases/latest": {"tag_name": "v0.4.0"},
        API + "simonvanlierde/citesync/contents/src/citesync/MAPPING_SOURCE": {
            "content": base64.b64encode(b"tag v0.3.0\n").decode()
        },
        API + "codemeta/codemeta/tags?per_page=100": [{"name": "4.0"}, {"name": "3.1"}, {"name": "old"}],
        **dict.fromkeys(SCHEMA_URLS.values(), schema),
        "https://raw.githubusercontent.com/citation-file-format/citation-file-format/1.2.0/schema.json": schema,
    }
    plans = poll({"rows": [{"format": "pep621", "term": "name", "path": "name"}]}, before, responses.__getitem__)
    assert len(plans) == 3
    assert "name" in plans[0]["body"]
    assert plans[1]["title"] == "Update mapping pin to v0.4.0"
    assert plans[2]["title"] == "Review CodeMeta tag 4.0"


def test_publisher_fetches_closed_titles_and_publishes_once():
    existing = {"simonvanlierde/codemeta-drift": {"closed"}}
    created = []

    def create(plan: dict[str, str]) -> None:
        created.append(plan)
        existing[plan["repo"]].add(plan["title"])

    plans = [
        {"repo": "simonvanlierde/codemeta-drift", "title": title, "body": "review"}
        for title in ("closed", "new", "new")
    ]
    publish(plans, existing.__getitem__, create)
    publish(plans, existing.__getitem__, create)
    assert [plan["title"] for plan in created] == ["new"]


@pytest.mark.parametrize(
    "fetch",
    [
        lambda _: {"$schema": "http://json-schema.org/draft-07/schema#"},
        pytest.param(fetch_json, marks=pytest.mark.live),
    ],
)
def test_fetch_schema_contract(fetch: Callable[[str], Any]):
    try:
        schema = fetch("https://raw.githubusercontent.com/citation-file-format/citation-file-format/1.2.0/schema.json")
    except HTTPError as err:
        if err.code == 429:
            pytest.skip("schema source rate limited the live contract check")
        raise
    assert isinstance(schema, dict)
    assert isinstance(schema["$schema"], str)


def test_failed_poll_never_publishes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    def fail(*_args: object) -> None:
        msg = "schema fetch failed"
        raise OSError(msg)

    monkeypatch.setattr(runner, "poll", fail)
    monkeypatch.setattr(runner, "publish", lambda *_args: pytest.fail("must not publish after a failed fetch"))
    root = Path(__file__).resolve().parents[1]
    out = tmp_path / "drafts.json"
    monkeypatch.setattr("sys.argv", ["poll", "--root", str(root), "--out", str(out), "--publish"])
    with pytest.raises(OSError, match="schema fetch failed"):
        runner.main()
    assert not out.exists()
