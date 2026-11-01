import json
from pathlib import Path

import pytest

from codemeta_drift.cli import main, read_dir
from codemeta_drift.coverage import coverage, markdown, unreviewed, upstream
from codemeta_drift.export import FORMATS

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/mapping-3.1.json"
TAG_FILES = ROOT / "tests/fixtures/3.1"  # CodeMeta at 3.1, pinned by tests/fixtures/3.1.sha256


def mapping():
    return json.loads(EXAMPLE.read_text("utf-8"))


def statuses():
    return {(c["format"], c["term"]): c["status"] for c in coverage(mapping())["cells"]}


def test_docs_page_is_generated_from_the_example():
    # Regenerate as docs/development.md says, with a CodeMeta clone that has the tag.
    assert (ROOT / "docs/coverage.md").read_text("utf-8") == markdown(mapping(), read_dir(TAG_FILES))


def test_unreviewed_lists_every_other_crosswalk_by_shape():
    data = unreviewed(read_dir(TAG_FILES), mapping())
    names = [f["format"] for f in data["formats"]]
    assert len(names) == 16  # the 44 crosswalks at 3.1, less the 28 the mapping reviews
    assert "Zenodo" not in names
    assert "NodeJS" not in names
    found = {(c["format"], c["term"]): c["status"] for c in data["cells"]}
    assert len(found) == 16 * 17
    assert found["ASCL", "name"] == "path"
    assert found["DCAT", "name"] == "path"  # dcterms:title, a prefixed key since schema 1.6
    assert found["MODS", "name"] == "prose"
    assert found["ASCL", "version"] == "empty"
    assert {f["label"] for f in data["formats"] if f["format"] == "DCAT"} == {"DCAT-2"}


def test_unreviewed_marks_a_cell_it_cannot_join():
    files = read_dir(TAG_FILES)
    ascl = "crosswalks/ASCL.csv"
    files[ascl] = files[ascl].replace("\nversion,", "\nversion,\nversion,", 1)
    found = {(c["format"], c["term"]): c["status"] for c in unreviewed(files, mapping())["cells"]}
    assert found["ASCL", "version"] == "unmatched"


def test_a_format_the_mapping_lacks_counts_as_not_reviewed():
    partial = mapping()
    partial["rows"] = [row for row in partial["rows"] if row["format"] != "bibtex"]
    assert "bibtex" not in coverage(partial)["formats"]
    files = read_dir(TAG_FILES)
    assert "BibTeX" in [f["format"] for f in unreviewed(files, partial)["formats"]]
    assert "| bibtex |" not in markdown(partial, files)


def test_cli_lists_unreviewed_crosswalks_from_the_tag(repo: Path, capsys: pytest.CaptureFixture[str]):
    assert main(["hub", "coverage", str(EXAMPLE), "--json", "--codemeta", str(repo)]) == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data["unreviewed"]["formats"]) == 16


def test_cli_coverage_without_the_tag_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    assert main(["hub", "coverage", str(EXAMPLE), "--codemeta", str(tmp_path)]) == 2
    assert capsys.readouterr().err.startswith(f"codemeta-drift: cannot read {tmp_path}: fatal:")


def test_known_cells_get_their_status():
    found = statuses()
    assert found["cff-1.2.0", "name"] == "as-is"
    assert found["cargo", "name"] == "corrected"  # the cell says package.authors
    assert found["npm", "identifier"] == "corrected"  # the cell says name, and npm has no DOI field
    assert found["cargo", "description"] == "added"  # no cell, though Cargo has package.description
    assert found["cargo", "datePublished"] == "no field"
    # The contributor person rows reuse the Person cells, but CFF has no contributor list to hold them.
    assert found["cff-1.2.0", "contributor.givenName"] == "no field"
    assert found["cff-1.2.0", "author.givenName"] == "as-is"  # the same Person row, with an author list
    assert found["pep621", "contributor.@id"] == "no field"
    assert not any(fmt == "codemeta" for fmt, _ in found)


def test_counts_for_the_crosswalks():
    found = [s for (fmt, _), s in statuses().items() if FORMATS[fmt].crosswalk]
    assert {s: found.count(s) for s in set(found)} == {"as-is": 112, "corrected": 123, "added": 90, "no field": 151}


def test_cli_writes_json(capsys: pytest.CaptureFixture[str]):
    assert main(["hub", "coverage", str(EXAMPLE), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["codemeta_tag"] == "3.1"
    assert len(data["cells"]) == 31 * 17
    assert "unreviewed" not in data  # only with --codemeta


def test_upstream_reports_unmatched_changed_and_fixed_cells():
    files = read_dir(ROOT / "tests/fixtures/3.1")
    assert upstream(files, mapping()) == []
    cargo = "crosswalks/Cargo.csv"
    files[cargo] = files[cargo].replace("keywords,package.keyword", "keywords,package.keywords")
    files[cargo] = files[cargo].replace("version,package.version", "version,package.ver")
    zenodo = "crosswalks/Zenodo.csv"
    files[zenodo] = files[zenodo].replace("\nversion,", "\nversion,\nversion,", 1)
    cff = "crosswalks/Citation File Format 1.2.0.csv"
    files[cff] = files[cff].replace("\nname,title", "\nname,name", 1)
    found = {(c["format"], c["term"]): c["state"] for c in upstream(files, mapping())}
    assert found == {
        ("cargo", "keywords"): "fixed",
        ("cargo", "version"): "changed",
        ("zenodo", "version"): "unmatched",
        ("cff-1.2.0", "name"): "changed",  # an as-is cell that changes is never "fixed"
    }


@pytest.mark.parametrize(
    ("cell", "term"),
    [
        ("identifier,ORCID", "author.@id"),  # Zenodo: orcid derives to creators[].orcid
        ("identifier,ORCID", "contributor.@id"),
    ],
)
def test_upstream_derives_the_new_cell_before_calling_it_fixed(cell: str, term: str):
    files = read_dir(ROOT / "tests/fixtures/3.1")
    zenodo = "crosswalks/Zenodo.csv"
    assert cell in files[zenodo]
    files[zenodo] = files[zenodo].replace(cell, "identifier,orcid")
    found = {(c["format"], c["term"]): c["state"] for c in upstream(files, mapping())}
    assert found["zenodo", term] == "fixed"


def test_an_emptied_cell_is_not_a_fix_for_a_format_with_no_field():
    files = read_dir(ROOT / "tests/fixtures/3.1")
    npm = "crosswalks/NodeJS.csv"
    assert "\nidentifier,name" in files[npm]
    files[npm] = files[npm].replace("\nidentifier,name", "\nidentifier,", 1)
    found = {(c["format"], c["term"]): c["state"] for c in upstream(files, mapping())}
    # The export would refuse that empty cell without its curated row, so the row must stay.
    assert found["npm", "identifier"] == "changed"


def test_upstream_says_missing_when_a_crosswalk_is_gone():
    files = read_dir(ROOT / "tests/fixtures/3.1")
    del files["crosswalks/Cargo.csv"]
    states = {c["state"] for c in upstream(files, mapping()) if c["format"] == "cargo"}
    assert states == {"missing"}


@pytest.mark.parametrize(
    ("reason", "shown"),
    [
        ("a repository is written git+https://host/path.git; see it", "written `git+https://host/path.git`; see it."),
        ("it says see (https://example.org/x) here", "see (`https://example.org/x`) here."),
        ("it ends at https://example.org/x. Next", "ends at `https://example.org/x`. Next."),
        ("it has an autolink <https://example.org/x> stays", "an autolink <https://example.org/x> stays."),
        ("it is already `https://example.org/x` code", "already `https://example.org/x` code."),
    ],
)
def test_a_url_in_a_reason_is_shown_as_code(reason: str, shown: str):
    data = mapping()
    row = next(r for r in data["rows"] if r["format"] == "cargo" and r["source"].startswith("curated:"))
    row["source"] = f"curated:{reason}"
    assert shown in markdown(data)
