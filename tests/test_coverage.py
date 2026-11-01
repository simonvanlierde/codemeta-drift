import json
from pathlib import Path

import pytest

from codemeta_drift.cli import main, read_dir
from codemeta_drift.coverage import coverage, markdown, upstream

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/mapping-3.1.json"


def mapping():
    return json.loads(EXAMPLE.read_text("utf-8"))


def statuses():
    return {(c["format"], c["term"]): c["status"] for c in coverage(mapping())["cells"]}


def test_docs_page_is_generated_from_the_example():
    # Regenerate with: uv run codemeta-drift hub coverage examples/mapping-3.1.json --out docs/coverage.md
    assert (ROOT / "docs/coverage.md").read_text("utf-8") == markdown(mapping())


def test_known_cells_get_their_status():
    found = statuses()
    assert found["cff-1.2.0", "name"] == "as-is"
    assert found["cargo", "name"] == "corrected"  # the cell says package.authors
    assert found["npm", "identifier"] == "corrected"  # the cell says name, and npm has no DOI field
    assert found["cargo", "description"] == "added"  # no cell, though Cargo has package.description
    assert found["cargo", "datePublished"] == "no field"
    # The contributor person rows reuse the Person cells, but CFF has no contributor list to hold them.
    assert found["cff-1.2.0", "contributor.givenName"] == "no field"
    assert not any(fmt == "codemeta" for fmt, _ in found)


def test_counts_for_the_four_crosswalks():
    found = [s for (fmt, _), s in statuses().items() if fmt != "pep621"]
    assert {s: found.count(s) for s in set(found)} == {"as-is": 27, "corrected": 15, "added": 12, "no field": 14}


def test_cli_writes_json(capsys: pytest.CaptureFixture[str]):
    assert main(["hub", "coverage", str(EXAMPLE), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["codemeta_tag"] == "3.1"
    assert len(data["cells"]) == 5 * 17


def test_upstream_reports_unmatched_changed_and_fixed_cells():
    files = read_dir(ROOT / "tests/fixtures/3.1")
    assert upstream(files, mapping()) == []
    cargo = "crosswalks/Cargo.csv"
    files[cargo] = files[cargo].replace("keywords,package.keyword", "keywords,package.keywords")
    files[cargo] = files[cargo].replace("version,package.version", "version,package.ver")
    zenodo = "crosswalks/Zenodo.csv"
    files[zenodo] = files[zenodo].replace("\nversion,", "\nversion,\nversion,", 1)
    found = {(c["format"], c["term"]): c["state"] for c in upstream(files, mapping())}
    assert found == {
        ("cargo", "keywords"): "fixed",
        ("cargo", "version"): "changed",
        ("zenodo", "version"): "unmatched",
    }
