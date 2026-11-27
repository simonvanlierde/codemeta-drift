import csv
import io
import json
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

from codemeta_drift.cli import main
from codemeta_drift.export import SCHEMA_VERSION, curated_tags
from codemeta_drift.hub import pair_rows, sssom, validate_mapping

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(params=curated_tags())
def example(request: pytest.FixtureRequest) -> Path:
    return ROOT / f"examples/mapping-{request.param}.json"


@pytest.fixture
def mapping(example: Path):
    return json.loads(example.read_text("utf-8"))


def test_pair_matches_hand_written_pep621_cargo(mapping: dict):
    rows = pair_rows(mapping, "pep621", "cargo")
    by_term = {row["term"]: row for row in rows}
    assert by_term["name"] == {"term": "name", "source": "project.name", "target": "package.name"}
    assert by_term["author.givenName"] == {
        "term": "author.givenName",
        "source": "project.authors[].name",
        "target": "package.authors[]",
    }
    assert "identifier" not in by_term


def test_go_spoke_only_has_repository_correspondence(mapping: dict):
    assert pair_rows(mapping, "gomod", "cargo") == [
        {"term": "codeRepository", "source": "module", "target": "package.repository"}
    ]


@pytest.mark.parametrize("fmt", ["missing", ""])
def test_pair_rejects_missing_format(mapping: dict, fmt: str):
    with pytest.raises(ValueError, match="format"):
        pair_rows(mapping, fmt, "cargo")


def test_coverage_of_a_row_with_an_unknown_kind_exits_3(
    mapping: dict, tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    """Not a KeyError (exit 1, as if it were findings) and not a status the report does not list."""
    mapping["rows"][0]["kind"] = "bogus"
    path = tmp_path / "mapping.json"
    path.write_text(json.dumps(mapping), "utf-8")
    assert main(["hub", "coverage", str(path)]) == 3
    assert "invalid or unsupported mapping row 1" in capsys.readouterr().err


def test_sssom_header_names_the_set_and_its_prefixes(mapping: dict):
    text = sssom(mapping)
    # The metadata block is YAML behind "# ", as SSSOM readers parse it.
    header = yaml.safe_load("\n".join(line[2:] for line in text.splitlines() if line.startswith("#")))
    site = "https://w3id.org/codemeta-drift/"
    assert header == {
        "mapping_set_id": f"{site}spokes-{mapping['codemeta_tag']}.sssom.tsv",
        "mapping_set_version": mapping["generator"]["version"],
        "mapping_set_title": f"codemeta-drift crosswalk hub spokes for CodeMeta {mapping['codemeta_tag']}",
        "mapping_set_description": header["mapping_set_description"],
        "mapping_provider": "https://github.com/simonvanlierde/codemeta-drift/",
        "creator_id": ["orcid:0009-0006-6953-909X"],
        "see_also": ["https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/crosswalk-hub.md"],
        "license": "https://spdx.org/licenses/Apache-2.0.html",
        "sssom_version": "1.0",
        "curie_map": {
            "term": f"{site}#term/",
            "field": f"{site}#field/",
            "format": f"{site}#format/",
            "orcid": "https://orcid.org/",
            "skos": "http://www.w3.org/2004/02/skos/core#",
            "semapv": "https://w3id.org/semapv/vocab/",
            # CodeMeta's context prefix at the tag: 4.0 moved schema.org to https.
            "schema": "http://schema.org/" if mapping["codemeta_tag"] == "3.1" else "https://schema.org/",
            "codemeta": "https://codemeta.github.io/terms/"
            if mapping["codemeta_tag"] == "3.1"
            else "https://w3id.org/codemeta/terms/",
        },
    }
    assert "may need conversion" in header["mapping_set_description"]
    # Counted from the rows, with Go's spoke, so a new format can't leave the number stale.
    formats = len({row["format"] for row in mapping["rows"]}) + 1
    assert f"from {formats} metadata formats" in header["mapping_set_description"]


def test_sssom_header_keeps_a_one_dot_zero_version_a_string(mapping: dict):
    data = mapping
    data["generator"]["version"] = "1.0"
    header = yaml.safe_load("\n".join(line[2:] for line in sssom(data).splitlines() if line.startswith("#")))
    assert header["mapping_set_version"] == "1.0"


def test_sssom_rows_run_from_format_fields_to_codemeta_terms(mapping: dict):
    text = sssom(mapping)
    rows = list(
        csv.DictReader(
            io.StringIO("\n".join(line for line in text.splitlines() if not line.startswith("#"))), delimiter="\t"
        )
    )
    expected_formats = {
        "format:cff-1.2.0",
        "format:codemeta",
        "format:crossref",
        "format:arxiv",
        "format:cff-preferred",
        "format:zenodo",
        "format:pep621",
        "format:cargo",
        "format:npm",
        "format:composer",
        "format:pkg-info",
        "format:r-description",
        "format:julia",
        "format:bibtex",
        "format:datacite",
        "format:setup-py",
        "format:ruby-gem",
        "format:maven",
        "format:cpan-meta-2",
        "format:nuget",
        "format:pubspec",
        "format:cabal",
        "format:typst",
        "format:quarto",
        "format:ris",
        "format:endnote",
        "format:github",
        "format:figshare",
        "format:bio-tools",
        "format:leiningen",
        "format:octave",
        "format:publiccode-0.8",
        "format:swmath",
        "format:spdx-2.3",
        "format:codemeta-2",
        "format:dcat-3",
        "format:doap",
        "format:wikidata",
        "format:gomod",
        "format:ro-crate",
        "format:croissant",
        "format:dublin-core",
        "format:debian",
        "format:mods",
        "format:vivo-1.8",
        "format:spase-2.6.1",
        "format:iso-19115-1-2014",
    }
    if mapping["codemeta_tag"] != "3.1":
        expected_formats |= {"format:gitlab", "format:code-json-2.0"}
    assert {row["subject_source"] for row in rows} == expected_formats
    for row in rows:
        assert row["mapping_justification"] == "semapv:ManualMappingCuration"
        assert row["subject_id"].startswith(f"field:{row['subject_source'].removeprefix('format:')}/")
        hub_term = row["object_id"].startswith("term:")
        assert hub_term or row["object_id"].startswith(("schema:", "codemeta:"))
        context = "" if hub_term else f"https://w3id.org/codemeta/{mapping['codemeta_tag']}"
        assert (row["object_source"], row["object_source_version"] != "") == (context, not hub_term)
        exact = row["predicate_id"] == "skos:exactMatch"
        assert exact or row["predicate_id"] == "skos:relatedMatch"
        assert exact == (row["see_also"] != ""), "an exactMatch row names its evidence"
    go = [row for row in rows if row["subject_source"] == "format:gomod"]
    assert [(row["subject_id"], row["object_id"]) for row in go] == [("field:gomod/module", "schema:codeRepository")]


def _rows(mapping: dict, fmt: str) -> dict[str, dict[str, str]]:
    text = "\n".join(line for line in sssom(mapping).splitlines() if not line.startswith("#"))
    rows = csv.DictReader(io.StringIO(text), delimiter="\t")
    return {row["object_label"]: row for row in rows if row["subject_source"] == f"format:{fmt}"}


def test_sssom_datacite_rows_follow_codemetas_sssom_methodology(mapping: dict):
    """Subjects are format fields and objects CodeMeta terms; a person sub-term's object is its own property.

    exactMatch only where CodeMeta's DataCite sheet marks the same field exact_match; a hub term only where
    CodeMeta has none.
    """
    rows = _rows(mapping, "datacite")
    exact = {
        "name": "schema:name",
        "version": "schema:version",
        "author": "schema:author",
        "author.givenName": "schema:givenName",
        "author.familyName": "schema:familyName",
        "contributor": "schema:contributor",
        "contributor.givenName": "schema:givenName",
        "contributor.familyName": "schema:familyName",
        "identifier": "schema:identifier",
        "keywords": "schema:keywords",
    }
    related = {
        "author.@id": "term:author.%40id",
        "contributor.@id": "term:contributor.%40id",
        "license": "schema:license",
        "swhid": "term:swhid",
        "codeRepository": "schema:codeRepository",
        "description": "schema:description",
        "datePublished": "schema:datePublished",
        "publisher": "schema:publisher",
        "resourceType": "term:resourceType",
        # Citation terms: a property where the property table has one, else the hub's own id.
        "author.name": "schema:name",
        "url": "schema:url",
        "contributor.name": "term:contributor.name",
        "author.resourceType": "term:author.resourceType",
        "contributor.resourceType": "term:contributor.resourceType",
        "isVersionOf": "term:isVersionOf",
        "hasVersion": "term:hasVersion",
    }
    assert {term: row["object_id"] for term, row in rows.items()} == exact | related
    assert {term for term, row in rows.items() if row["predicate_id"] == "skos:exactMatch"} == exact.keys()
    assert "/datacite/" in rows["version"]["see_also"]
    assert rows["author.givenName"]["subject_id"] == "field:datacite/creators%5B%5D.givenName"
    assert rows["author.givenName"]["subject_label"] == "creators[].givenName"


def test_sssom_objects_are_terms_of_the_tags_context(mapping: dict):
    """A schema: or codemeta: object is a term CodeMeta's context defines, not an IRI the hub made up."""
    tag = mapping["codemeta_tag"]
    context = json.loads((ROOT / f"tests/fixtures/{tag}/codemeta.jsonld").read_text("utf-8"))["@context"]
    ids = {value["@id"] if isinstance(value, dict) else value for value in context.values()}
    text = "\n".join(line for line in sssom(mapping).splitlines() if not line.startswith("#"))
    objects = {row["object_id"] for row in csv.DictReader(io.StringIO(text), delimiter="\t")}
    assert {o for o in objects if not o.startswith("term:")} <= ids


def test_a_citation_term_on_a_codemeta_property_gets_its_codemeta_id(mapping: dict):
    assert _rows(mapping, "cff-1.2.0")["preferredCitation"]["object_id"] == "codemeta:referencePublication"


def test_sssom_exact_match_lapses_when_the_checked_path_changes(mapping: dict):
    row = next(r for r in mapping["rows"] if (r["format"], r["term"]) == ("datacite", "version"))
    row["path"] = "versions[].version"
    assert _rows(mapping, "datacite")["version"]["predicate_id"] == "skos:relatedMatch"


def test_sssom_prefixes_have_distinct_uri_namespaces(mapping: dict):
    prefixes = {}
    curie_map = sssom(mapping).split("# curie_map:\n", 1)[1]
    for line in curie_map.splitlines():
        if line.startswith("#   "):
            prefix, uri = line.removeprefix("#   ").split(": ", 1)
            prefixes[prefix] = uri
    assert len(set(prefixes.values())) == len(prefixes), "SSSOM readers reject duplicate URI prefixes"


def test_cli_writes_pair_csv(example: Path, capsys: pytest.CaptureFixture[str]):
    assert main(["hub", "pair", str(example), "--from", "gomod", "--to", "cargo"]) == 0
    assert capsys.readouterr().out == "term,source,target\ncodeRepository,module,package.repository\n"


def test_cli_rejects_bad_mapping_without_partial_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    source = tmp_path / "mapping.json"
    source.write_text('{"schema_version":"2.0"}')
    assert main(["hub", "sssom", str(source)]) == 3
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "codemeta-drift:" in captured.err


def test_crosswalk_preserves_table_order_and_duplicate_properties(
    example: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    (tmp_path / "properties_description.csv").write_text(
        "Parent Type,Property\nschema:Person,identifier\nschema:Thing,identifier\nschema:Thing,name\n"
        "schema:Thing,unknown\nschema:CreativeWork,contributor\n"
    )
    assert main(["hub", "crosswalk", str(example), str(tmp_path), "--format", "cff-1.2.0"]) == 0
    assert capsys.readouterr().out == (
        "Property,cff-1.2.0\nidentifier,authors[].orcid\n"
        "identifier,doi | identifiers[type=doi].value\nname,title\nunknown,\ncontributor,\n"
    )


@pytest.mark.parametrize("cell", [[], {}, 7, True])
def test_hub_rejects_malformed_original_cells(mapping: dict, cell: object):
    data = mapping
    data["rows"][0]["crosswalk_cell"] = cell
    with pytest.raises(ValueError, match="mapping row"):
        validate_mapping(data)


def test_cli_writes_sssom_to_out_and_nothing_to_stdout(
    mapping: dict, example: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    out = tmp_path / "spokes.sssom.tsv"
    assert main(["hub", "sssom", str(example), "--out", str(out)]) == 0
    assert capsys.readouterr().out == ""
    assert out.read_text("utf-8") == sssom(mapping)


def test_cli_coverage_prints_markdown_and_json_on_request(
    mapping: dict, example: Path, capsys: pytest.CaptureFixture[str]
):
    assert main(["hub", "coverage", str(example)]) == 0
    text = capsys.readouterr().out
    assert f"\n# Crosswalk coverage at CodeMeta {mapping['codemeta_tag']}\n" in text
    assert "| Mark | Status | Meaning |" in text
    assert main(["hub", "coverage", str(example), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["codemeta_tag"] == mapping["codemeta_tag"]


def test_a_row_from_a_newer_minor_says_to_upgrade(mapping: dict):
    mapping["schema_version"] = "1.99"
    mapping["rows"][0]["format"] = "future-format"
    with pytest.raises(ValueError, match=r"row 1 \(schema_version 1\.99 is newer than this build's 1\.\d+; upgrade"):
        validate_mapping(mapping)


@pytest.mark.parametrize("version", ["1.0", SCHEMA_VERSION])
def test_a_row_from_an_older_or_the_current_minor_is_not_called_newer(mapping: dict, version: str):
    mapping["schema_version"] = version
    mapping["rows"][0]["format"] = "future-format"
    with pytest.raises(ValueError, match=r"row 1$"):
        validate_mapping(mapping)


@pytest.mark.parametrize("data", [[], {"schema_version": 1.0}])
def test_mapping_must_be_an_object_with_a_version_string(data: object):
    with pytest.raises(ValueError, match="schema_version string"):
        validate_mapping(data)


def _without_cargo(mapping: dict, tmp_path: Path) -> Path:
    mapping["rows"] = [row for row in mapping["rows"] if row["format"] != "cargo"]
    path = tmp_path / "mapping.json"
    path.write_text(json.dumps(mapping))
    return path


def test_crosswalk_rejects_a_format_the_mapping_has_no_rows_for(
    mapping: dict, tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    (tmp_path / "properties_description.csv").write_text("Parent Type,Property\nschema:Thing,name\n")
    path = _without_cargo(mapping, tmp_path)
    assert main(["hub", "crosswalk", str(path), str(tmp_path), "--format", "cargo"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unknown format 'cargo'" in captured.err


@pytest.mark.parametrize("argv", [["crosswalk", ".", "--format", "nope"], ["pair", "--from", "nope", "--to", "cargo"]])
def test_an_unknown_format_id_is_refused_by_the_parser_with_the_choices(
    argv: list[str], example: Path, capsys: pytest.CaptureFixture[str]
):
    with pytest.raises(SystemExit) as exit_:
        main(["hub", argv[0], str(example), *argv[1:]])
    assert exit_.value.code == 2
    assert "invalid choice: 'nope' (choose from" in capsys.readouterr().err


def test_hub_help_lists_every_format(capsys: pytest.CaptureFixture[str]):
    with pytest.raises(SystemExit):
        main(["hub", "--help"])
    assert "cargo" in capsys.readouterr().out


def test_hub_reads_the_mapping_from_standard_input(
    example: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    assert main(["hub", "sssom", str(example)]) == 0
    expected = capsys.readouterr().out
    monkeypatch.setattr("sys.stdin", io.StringIO(example.read_text("utf-8")))
    assert main(["hub", "sssom", "-"]) == 0
    assert capsys.readouterr().out == expected


def test_hub_json_wraps_each_output_in_the_report(example: Path, capsys: pytest.CaptureFixture[str]):
    assert main(["hub", "pair", str(example), "--from", "gomod", "--to", "cargo", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert (report["schema_version"], report["errors"]) == (1, [])
    assert report["rows"] == [{"term": "codeRepository", "source": "module", "target": "package.repository"}]


@pytest.mark.parametrize("as_json", [True, False])
def test_pair_usage_error_is_json_on_stdout_or_a_line_on_stderr(
    mapping: dict, tmp_path: Path, capsys: pytest.CaptureFixture[str], *, as_json: bool
):
    path = _without_cargo(mapping, tmp_path)
    assert main(["hub", "pair", str(path), "--from", "cargo", "--to", "zenodo", *(["--json"] if as_json else [])]) == 2
    captured = capsys.readouterr()
    message = "source and target must be present formats"
    if as_json:
        assert captured.err == ""
        assert message in json.loads(captured.out)["errors"][0]["message"]
    else:
        assert captured.out == ""
        assert captured.err.startswith(f"codemeta-drift: {message}")


@pytest.mark.parametrize("fmt", ["gitlab", "code-json-2.0"])
def test_mapping_rejects_a_format_before_its_first_tag(mapping: dict, fmt: str):
    mapping["codemeta_tag"] = "3.1"
    mapping["rows"] = [{"format": fmt, "term": "name", "path": "name", "source": "curated:test"}]
    with pytest.raises(ValueError, match="mapping row"):
        validate_mapping(mapping)


@pytest.mark.parametrize("tag", ["main", "v4.0", "4..0", "--help", "4.0\n", "\u0664.\u0660"])
def test_mapping_rejects_non_numeric_tags(mapping: dict, tag: str):
    mapping["codemeta_tag"] = tag
    with pytest.raises(ValueError, match="codemeta_tag"):
        validate_mapping(mapping)


DAMAGE = {
    "version": lambda d: d.update(schema_version="2.0"),
    "duplicate": lambda d: d["rows"].append(d["rows"][0]),
    "path": lambda d: d["rows"][0].update(path="authors[][]"),
    "type": lambda d: d["rows"][0].update(format=3),
    "source": lambda d: d["rows"][0].pop("source"),
    "generator": lambda d: d.update(generator={"name": 1, "version": None}),
    "kind": lambda d: d["rows"][0].update(kind="bogus"),
    "rows": lambda d: d.update(rows=None),
    "no-tag": lambda d: d.pop("codemeta_tag"),
    "empty-tag": lambda d: d.update(codemeta_tag=""),
    "no-generator": lambda d: d.update(generator=None),
    "empty-generator-name": lambda d: d["generator"].update(name=""),
    "generator-version-not-string": lambda d: d["generator"].update(version=1),
    "rows-not-list": lambda d: d.update(rows={}),
    "row-not-object": lambda d: d["rows"].insert(0, "row"),
    "row-missing-term": lambda d: d["rows"][0].pop("term"),
    "unknown-format": lambda d: d["rows"][0].update(format="nonesuch"),
    "term-not-string": lambda d: d["rows"][0].update(term=None),
    "unknown-term": lambda d: d["rows"][0].update(term="nonesuch"),
    "source-not-string": lambda d: d["rows"][0].update(source=7),
    "source-bad-pattern": lambda d: d["rows"][0].update(source="elsewhere"),
    "comment-not-string": lambda d: d["rows"][0].update(comment=7),
    "see-also-not-string": lambda d: d["rows"][0].update(see_also=7),
    "see-also-not-https": lambda d: d["rows"][0].update(see_also="http://example.org"),
    "path-not-string": lambda d: d["rows"][0].update(path=7),
}


@pytest.mark.parametrize("damage", DAMAGE.values(), ids=DAMAGE.keys())
def test_each_single_flaw_in_a_mapping_is_rejected(mapping: dict, damage: Callable[[dict], object]):
    damage(mapping)
    with pytest.raises(ValueError, match="mapping"):
        validate_mapping(mapping)


def test_a_row_with_an_https_see_also_is_accepted(mapping: dict):
    mapping["rows"][0]["see_also"] = "https://example.org/x"
    mapping["rows"][0]["comment"] = "why"
    validate_mapping(mapping)
