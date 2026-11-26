import json
import re
from pathlib import Path

import pytest

from codemeta_drift.cli import main
from codemeta_drift.conformance import SCHEMA_FILES
from codemeta_drift.watcher import issue_plans, pin_tag, schema_changes, schema_paths


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


def test_a_new_pyproject_tool_table_needs_no_row(schemas: dict):
    after = json.loads(json.dumps(schemas))
    after["pep621"]["properties"]["tool"] = {"properties": {"simplint": {"type": "object"}}}
    after["pep621"]["properties"]["toolkit"] = {"type": "string"}
    changes = schema_changes([{"format": "pep621", "term": "name", "path": "project.name"}], schemas, after)
    assert [c["path"] for c in changes] == ["toolkit"]


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
    report = json.loads(capsys.readouterr().out)
    assert (report["schema_version"], report["findings"], report["errors"]) == (1, [], [])
    plans = report["issues"]
    assert len(plans) == 2
    assert "project.title" in plans[0]["body"]
    existing.write_text(json.dumps([plan["title"] for plan in plans]))
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)["issues"] == []
    existing.write_text("{}")
    assert main(args) == 3
    captured = capsys.readouterr()
    assert captured.err == ""
    assert "JSON list of titles" in json.loads(captured.out)["errors"][0]["message"]


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


def test_a_backtick_in_a_schema_path_keeps_the_code_span_closed():
    changes = [{"format": "npm", "kind": "unmapped", "path": "a`@x", "detail": "new field has no mapping row"}]
    [plan] = issue_plans(changes, "v1.0.0", "v1.0.0", set())
    assert "- npm: unmapped ``a`@x`` (new" in plan["body"]


@pytest.mark.parametrize("source", ["tag \n", "tag\n", "tag v1\ntag v2\n", ""])
def test_pin_tag_needs_exactly_one_tag_line_with_a_value(source: str):
    with pytest.raises(ValueError, match="exactly one tag line"):
        pin_tag(source)


def test_issue_plans_have_a_stable_title_and_exact_bodies():
    changes = [{"format": "pep621", "kind": "broken", "path": "project.name", "detail": "no 'name'"}]
    reordered = [dict(reversed(changes[0].items()))]
    schema, pin = issue_plans(changes, "v0.3.0", "v0.4.0", set())
    assert issue_plans(reordered, "v0.4.0", "v0.4.0", set())[0]["title"] == schema["title"]
    assert re.fullmatch(r"Review schema changes [0-9a-f]{12}", schema["title"])
    assert schema == {
        "repo": "simonvanlierde/codemeta-drift",
        "title": schema["title"],
        "body": "These schema fields need review:\n\n- pep621: broken `project.name` (no 'name')",
    }
    assert pin == {
        "repo": "simonvanlierde/citesync",
        "title": "Update mapping pin to v0.4.0",
        "body": "The mapping pin is v0.3.0; the latest stable mapping release is v0.4.0.\n"
        "Review the export and update MAPPING_SOURCE with its matching files and hashes.",
    }


def test_different_changes_get_different_titles():
    one = [{"format": "pep621", "kind": "broken", "path": "a", "detail": "x"}]
    two = [{"format": "pep621", "kind": "broken", "path": "b", "detail": "x"}]
    assert (
        issue_plans(one, "v1.0.0", "v1.0.0", set())[0]["title"]
        != issue_plans(two, "v1.0.0", "v1.0.0", set())[0]["title"]
    )


def test_schema_paths_keep_siblings_after_a_repeated_branch_and_merge_item_paths():
    shared = {"properties": {"x": {}}}
    schema = {
        "properties": {
            "a": shared,
            "b": shared,
            "authors": {"type": "array", "items": {"properties": {"name": {}}}},
            "tags": {"type": "array", "items": {"properties": {"label": {}}}},
        }
    }
    assert schema_paths(schema) == {
        "a", "a.x", "b", "b.x", "authors", "authors[].name", "tags", "tags[].label",
    }  # fmt: skip


def test_a_new_list_item_field_is_covered_by_a_row_naming_its_list():
    before = {"pep621": {"properties": {"authors": {"type": "array", "items": {"properties": {"name": {}}}}}}}
    after = {
        "pep621": {"properties": {"authors": {"type": "array", "items": {"properties": {"name": {}, "email": {}}}}}}
    }
    rows = [{"format": "pep621", "term": "author.name", "path": "authors[].name"}]
    assert [c["path"] for c in schema_changes(rows, before, after)] == ["authors[].email"]
    rows.append({"format": "pep621", "term": "author.email", "path": "authors[].email"})
    assert schema_changes(rows, before, after) == []


def test_a_new_tool_array_item_field_needs_no_row():
    after = {"pep621": {"properties": {"tool": {"type": "array", "items": {"properties": {"x": {}}}}}}}
    before = {"pep621": {"properties": {}}}
    assert schema_changes([], before, after) == []


def test_unequal_format_sets_are_refused():
    with pytest.raises(ValueError, match="same format schemas"):
        schema_changes([], {"pep621": {}}, {"cargo": {}})


def test_pin_tag_needs_exactly_one_tag_line():
    assert pin_tag("commit x\ntag v1.2.3\n") == "v1.2.3"
    for source in ("commit x\n", "tag v1\ntag v2\n"):
        with pytest.raises(ValueError, match="MAPPING_SOURCE must contain exactly one tag line"):
            pin_tag(source)
