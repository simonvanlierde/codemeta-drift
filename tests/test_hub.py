import csv
import io
import json
from pathlib import Path

import pytest
import yaml

from codemeta_drift.cli import main
from codemeta_drift.hub import pair_rows, sssom, validate_mapping

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/mapping-3.1.json"


def mapping():
    return json.loads(EXAMPLE.read_text("utf-8"))


def test_pair_matches_hand_written_pep621_cargo():
    rows = pair_rows(mapping(), "pep621", "cargo")
    by_term = {row["term"]: row for row in rows}
    assert by_term["name"] == {"term": "name", "source": "project.name", "target": "package.name"}
    assert by_term["author.givenName"] == {
        "term": "author.givenName",
        "source": "project.authors[].name",
        "target": "package.authors[]",
    }
    assert "identifier" not in by_term


def test_go_spoke_only_has_repository_correspondence():
    assert pair_rows(mapping(), "gomod", "cargo") == [
        {"term": "codeRepository", "source": "module", "target": "package.repository"}
    ]


@pytest.mark.parametrize("fmt", ["missing", ""])
def test_pair_rejects_missing_format(fmt: str):
    with pytest.raises(ValueError, match="format"):
        pair_rows(mapping(), fmt, "cargo")


@pytest.mark.parametrize("change", ["version", "duplicate", "path", "type", "source", "rows", "generator"])
def test_mapping_rejects_invalid_input(change: str):
    data = mapping()
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


def test_sssom_uses_curie_identifiers_and_conservative_predicates():
    text = sssom(mapping())
    # The metadata block is YAML behind "# ", as SSSOM readers parse it.
    header = yaml.safe_load("\n".join(line[2:] for line in text.splitlines() if line.startswith("#")))
    site = "https://simonvanlierde.com/codemeta-drift/"
    assert header == {
        "mapping_set_id": f"{site}spokes-3.1.sssom.tsv",
        "mapping_set_version": mapping()["generator"]["version"],
        "mapping_set_title": "codemeta-drift crosswalk hub spokes for CodeMeta 3.1",
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
    assert "and 33 metadata formats" in header["mapping_set_description"]


def test_sssom_header_keeps_a_one_dot_zero_version_a_string():
    data = mapping()
    data["generator"]["version"] = "1.0"
    header = yaml.safe_load("\n".join(line[2:] for line in sssom(data).splitlines() if line.startswith("#")))
    assert header["mapping_set_version"] == "1.0"


def test_sssom_rows_use_curie_identifiers_and_conservative_predicates():
    text = sssom(mapping())
    rows = list(
        csv.DictReader(
            io.StringIO("\n".join(line for line in text.splitlines() if not line.startswith("#"))), delimiter="\t"
        )
    )
    assert {row["object_source"] for row in rows} == {
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
    }
    for row in rows:
        assert row["mapping_justification"] == "semapv:ManualMappingCuration"
        assert row["predicate_id"] == "skos:relatedMatch"
        assert row["subject_id"].startswith("term:")
    go = [row for row in rows if row["object_source"] == "format:gomod"]
    assert [row["object_id"] for row in go] == ["field:gomod/module"]


def test_sssom_prefixes_have_distinct_uri_namespaces():
    prefixes = {}
    curie_map = sssom(mapping()).split("# curie_map:\n", 1)[1]
    for line in curie_map.splitlines():
        if line.startswith("#   "):
            prefix, uri = line.removeprefix("#   ").split(": ", 1)
            prefixes[prefix] = uri
    assert len(set(prefixes.values())) == len(prefixes), "SSSOM readers reject duplicate URI prefixes"


def test_cli_writes_pair_csv(capsys: pytest.CaptureFixture[str]):
    assert main(["hub", "pair", str(EXAMPLE), "--from", "gomod", "--to", "cargo"]) == 0
    assert capsys.readouterr().out == "term,source,target\ncodeRepository,module,package.repository\n"


def test_cli_rejects_bad_mapping_without_partial_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    source = tmp_path / "mapping.json"
    source.write_text('{"schema_version":"2.0"}')
    assert main(["hub", "sssom", str(source)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "codemeta-drift:" in captured.err


def test_crosswalk_preserves_table_order_and_duplicate_properties(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    (tmp_path / "properties_description.csv").write_text(
        "Parent Type,Property\nschema:Person,identifier\nschema:Thing,identifier\nschema:Thing,name\n"
        "schema:Thing,unknown\nschema:CreativeWork,contributor\n"
    )
    assert main(["hub", "crosswalk", str(EXAMPLE), str(tmp_path), "--format", "cff-1.2.0"]) == 0
    assert capsys.readouterr().out == (
        "Property,cff-1.2.0\nidentifier,authors[].orcid\n"
        "identifier,doi | identifiers[type=doi].value\nname,title\nunknown,\ncontributor,\n"
    )


@pytest.mark.parametrize("cell", [[], {}, 7, True])
def test_hub_rejects_malformed_original_cells(cell: object):
    data = mapping()
    data["rows"][0]["crosswalk_cell"] = cell
    with pytest.raises(ValueError, match="mapping row"):
        validate_mapping(data)
