import base64
import json
from collections.abc import Callable
from email.message import Message
from pathlib import Path
from typing import Any
from urllib.error import HTTPError

import pytest

from codemeta_drift import poll as runner
from codemeta_drift.poll import API, SCHEMA_URLS, fetch_json, poll, publish


@pytest.mark.parametrize("upstream", ["changed", "deleted", "rate-limited"])
def test_poll_uses_current_schemas_and_only_latest_codemeta_tag(upstream: str):
    schema = {"properties": {"title": {"type": "string"}}}
    before = {fmt: {"properties": {"name": {}}} for fmt in (*SCHEMA_URLS, "cff-1.2.0")}
    before["zenodo"] = json.loads((Path(__file__).parent / "fixtures/schemas/zenodo.json").read_text())
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
    source = before["zenodo"]["x-source"]
    responses.update(
        {API + source["repo"] + "/contents/" + path: {"sha": digest} for path, digest in source["files"].items()}
    )
    plans = poll({"rows": [{"format": "pep621", "term": "name", "path": "name"}]}, before, responses.__getitem__)
    assert len(plans) == 3
    assert "name" in plans[0]["body"]
    assert plans[1]["title"] == "Update mapping pin to v0.4.0"
    assert plans[2]["title"] == "Review CodeMeta tag 4.0"
    changed = next(iter(source["files"]))
    changed_url = API + source["repo"] + "/contents/" + changed

    def fetch(url: str) -> dict[str, Any] | list[dict[str, str]]:
        if url == changed_url:
            if upstream == "rate-limited":
                raise HTTPError(url, 429, "Too Many Requests", Message(), None)
            if upstream == "deleted":
                raise HTTPError(url, 404, "Not Found", Message(), None)
            return {"sha": "b" * 40}
        return responses[url]

    if upstream == "rate-limited":
        with pytest.raises(HTTPError) as caught:
            poll({"rows": []}, before, fetch)
        assert caught.value.code == 429
        return
    plans = poll({"rows": []}, before, fetch)
    importer = [plan for plan in plans if plan["title"].startswith("Review Zenodo importer")]
    assert len(importer) == 1
    assert importer[0]["title"].endswith("missing" if upstream == "deleted" else "b" * 40)
    assert any(plan["title"] == "Update mapping pin to v0.4.0" for plan in plans)
    created = []
    titles = {plan["repo"]: set() for plan in plans}

    def create(plan: dict[str, str]) -> None:
        created.append(plan)
        titles[plan["repo"]].add(plan["title"])

    publish(plans, titles.__getitem__, create)
    publish(plans, titles.__getitem__, create)
    assert created == plans


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


@pytest.mark.parametrize("live", [False, pytest.param(True, marks=pytest.mark.live)])
def test_zenodo_importer_source_contract(*, live: bool):
    source = json.loads((Path(__file__).parent / "fixtures/schemas/zenodo.json").read_text())["x-source"]
    for path in source["files"]:
        try:
            result = fetch_json(API + source["repo"] + "/contents/" + path) if live else {"sha": "a" * 40}
        except HTTPError as err:
            if err.code == 429:
                pytest.skip("Zenodo source contract check was rate limited")
            raise
        assert isinstance(result["sha"], str)
        assert len(result["sha"]) == 40
