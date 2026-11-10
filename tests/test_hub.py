import csv
import io
import json
from pathlib import Path

import pytest
import yaml

from codemeta_drift.cli import main
from codemeta_drift.export import curated_tags
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


@pytest.mark.parametrize("change", ["version", "duplicate", "path", "type", "source", "rows", "generator"])
def test_mapping_rejects_invalid_input(mapping: dict, change: str):
    data = mapping
    if change == "version":
        data["schema_version"] = "2.0"
    elif change == "duplicate":
        data["rows"].append(data["rows"][0])
    elif change == "path":
        data["rows"][0]["path"] = "authors[][]"
    elif change == "type":
        data["rows"][0]["format"] = 3
    elif change == "source":
        del data["rows"][0]["source"]
    elif change == "generator":
        data["generator"] = {"name": 1, "version": None}
    else:
        data["rows"] = None
    with pytest.raises(ValueError, match="mapping"):
        validate_mapping(data)


def test_sssom_uses_curie_identifiers_and_conservative_predicates(mapping: dict):
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
        },
    }
    assert "may need conversion" in header["mapping_set_description"]
    # Counted from the rows, with Go's spoke, so a new format can't leave the number stale.
    formats = {"3.1": 37, "4.0": 39}[mapping["codemeta_tag"]]
    assert f"and {formats} metadata formats" in header["mapping_set_description"]


def test_sssom_header_keeps_a_one_dot_zero_version_a_string(mapping: dict):
    data = mapping
    data["generator"]["version"] = "1.0"
    header = yaml.safe_load("\n".join(line[2:] for line in sssom(data).splitlines() if line.startswith("#")))
    assert header["mapping_set_version"] == "1.0"


def test_sssom_rows_use_curie_identifiers_and_conservative_predicates(mapping: dict):
    text = sssom(mapping)
    rows = list(
        csv.DictReader(
            io.StringIO("\n".join(line for line in text.splitlines() if not line.startswith("#"))), delimiter="\t"
        )
    )
    expected_formats = {
        "format:cff-1.2.0",
        "format:codemeta",
        "format:zenodo",
        "format:pep621",
        "format:cargo",
        "format:npm",
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
    }
    if mapping["codemeta_tag"] != "3.1":
        expected_formats |= {"format:gitlab", "format:code-json-2.0"}
    assert {row["object_source"] for row in rows} == expected_formats
    for row in rows:
        assert row["mapping_justification"] == "semapv:ManualMappingCuration"
        assert row["predicate_id"] == "skos:relatedMatch"
        assert row["subject_id"].startswith("term:")
    go = [row for row in rows if row["object_source"] == "format:gomod"]
    assert [row["object_id"] for row in go] == ["field:gomod/module"]


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
    assert text.startswith(f"# Crosswalk coverage at CodeMeta {mapping['codemeta_tag']}\n")
    assert "| Mark | Status | Meaning |" in text
    assert main(["hub", "coverage", str(example), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["codemeta_tag"] == mapping["codemeta_tag"]


@pytest.mark.parametrize("data", [[], {"schema_version": 1.0}])
def test_mapping_must_be_an_object_with_a_version_string(data: object):
    with pytest.raises(ValueError, match="schema_version string"):
        validate_mapping(data)


def test_crosswalk_rejects_a_format_the_mapping_has_no_rows_for(
    example: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    (tmp_path / "properties_description.csv").write_text("Parent Type,Property\nschema:Thing,name\n")
    assert main(["hub", "crosswalk", str(example), str(tmp_path), "--format", "nope"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unknown format 'nope'" in captured.err


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


def test_pair_with_a_format_the_mapping_has_no_rows_for_is_a_usage_error(
    example: Path, capsys: pytest.CaptureFixture[str]
):
    assert main(["hub", "pair", str(example), "--from", "nope", "--to", "zenodo"]) == 2
    assert "source and target must be present formats" in capsys.readouterr().err
