import json
from pathlib import Path

import pytest

from codemeta_drift.cli import main
from codemeta_drift.conformance import SCHEMA_FILES
from codemeta_drift.watcher import issue_plans, schema_changes, schema_paths


@pytest.fixture
def schemas():
    return {"pep621": {"properties": {"project": {"properties": {"name": {"type": "string"}}}}}}


def test_renamed_field_names_broken_and_new_paths(schemas: dict):
    after = {"pep621": {"properties": {"project": {"properties": {"title": {"type": "string"}}}}}}
    changes = schema_changes([{"format": "pep621", "term": "name", "path": "project.name"}], schemas, after)
    assert changes == [
        {"format": "pep621", "kind": "broken", "path": "project.name", "detail": "no 'name'"},
        {"format": "pep621", "kind": "unmapped", "path": "project.title", "detail": "new field has no mapping row"},
    ]


def test_a_row_outside_the_grammar_is_reported_not_raised(schemas: dict):
    changes = schema_changes([{"format": "pep621", "term": "name", "path": "project name"}], schemas, schemas)
    assert changes == [{"format": "pep621", "kind": "broken", "path": "project name", "detail": "not a path"}]


def test_unchanged_schema_does_not_report_existing_unmapped_fields(schemas: dict):
    assert schema_changes([], schemas, schemas) == []


def test_issue_plans_deduplicate_schema_changes_and_behind_pin():
    changes = [{"format": "pep621", "kind": "broken", "path": "project.name", "detail": "no 'name'"}]
    plans = issue_plans(changes, "v0.3.0", "v0.4.0", set())
    assert len(plans) == 2
    assert "project.name" in plans[0]["body"]
    assert plans[1]["repo"] == "simonvanlierde/citesync"
    assert issue_plans(changes, "v0.3.0", "v0.4.0", {plan["title"] for plan in plans}) == []
    assert issue_plans([], "v0.4.0", "v0.4.0", set()) == []


def test_a_newer_pin_is_not_behind():
    assert issue_plans([], "v0.5.0", "v0.4.0", set()) == []


def test_local_refs_arrays_and_recursive_refs_terminate():
    schema = {
        "$defs": {"person": {"properties": {"name": {}, "parent": {"$ref": "#/$defs/person"}}}},
        "properties": {"authors": {"type": "array", "items": {"$ref": "#/$defs/person"}}},
    }
    assert schema_paths(schema) == {"authors", "authors[].name", "authors[].parent"}


def test_cli_watch_previews_and_deduplicates(repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    for name in SCHEMA_FILES.values():
        (before / name).write_text('{"properties":{"project":{"properties":{"name":{}}}}}')
        (after / name).write_text('{"properties":{"project":{"properties":{"title":{}}}}}')
    source = tmp_path / "MAPPING_SOURCE"
    source.write_text("tag v0.3.0\ncommit example\n")
    existing = tmp_path / "existing.json"
    existing.write_text("[]")
    args = [
        "watch",
        str(repo),
        "--tag",
        "3.1",
        "--before",
        str(before),
        "--after",
        str(after),
        "--citesync-source",
        str(source),
        "--latest",
        "v0.4.0",
        "--existing",
        str(existing),
    ]
    assert main(args) == 0
    plans = json.loads(capsys.readouterr().out)
    assert len(plans) == 2
    assert "project.title" in plans[0]["body"]
    existing.write_text(json.dumps([plan["title"] for plan in plans]))
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out) == []
    existing.write_text("{}")
    assert main(args) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "JSON list of titles" in captured.err


@pytest.mark.parametrize("pin", ["v0.9.0", "0.9.0"])
def test_numeric_release_order(pin: str):
    assert len(issue_plans([], pin, "v0.10.0", set())) == 1


@pytest.mark.parametrize("pin", ["main", "v0.1", "v0.1.0-rc1"])
def test_bad_release_is_an_error(pin: str):
    with pytest.raises(ValueError, match="stable release tag"):
        issue_plans([], pin, "v0.10.0", set())


def test_alternatives_and_filter_paths_are_checked_separately():
    schema = {"properties": {"items": {"type": "array", "items": {"properties": {"type": {}, "value": {}}}}}}
    rows = [{"format": "cff-1.2.0", "term": "identifier", "path": "doi | items[type=doi].value"}]
    assert schema_changes(rows, {"cff-1.2.0": schema}, {"cff-1.2.0": schema}) == [
        {"format": "cff-1.2.0", "kind": "broken", "path": "doi", "detail": "no 'doi'"}
    ]


@pytest.mark.parametrize("bad", [None, [], {"properties": []}])
def test_malformed_schemas_are_errors(bad: object):
    with pytest.raises(ValueError, match="schema"):
        schema_changes([], {"pep621": {}}, {"pep621": bad})


def test_schema_paths_follow_refs_into_array_nodes():
    schema = {
        "allOf": [{"properties": {"hidden": {"type": "string"}}}],
        "properties": {"project": {"$ref": "#/allOf/0"}},
    }
    assert "project.hidden" in schema_paths(schema)


def test_mapped_arrays_and_filters_are_not_new_unmapped_fields():
    schema = {
        "properties": {
            "authors": {"type": "array", "items": {"properties": {"name": {}}}},
            "identifiers": {"type": "array", "items": {"properties": {"type": {}, "value": {}}}},
        }
    }
    rows = [
        {"format": "pep621", "term": "author", "path": "authors[]"},
        {"format": "pep621", "term": "author.givenName", "path": "authors[].name"},
        {"format": "pep621", "term": "identifier", "path": "identifiers[type=doi].value"},
    ]
    assert schema_changes(rows, {"pep621": {}}, {"pep621": schema}) == []


@pytest.mark.parametrize("key", ["items", "prefixItems"])
def test_schema_paths_include_tuple_arrays(key: str):
    schema = {"properties": {"authors": {"type": "array", key: [{"properties": {"name": {}}}]}}}
    assert "authors[].name" in schema_paths(schema)
