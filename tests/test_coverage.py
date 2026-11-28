import json
import re
from collections import Counter
from pathlib import Path

import pytest

from codemeta_drift.cli import main, read_dir
from codemeta_drift.coverage import (
    NOT_REVIEWED,
    SHAPES,
    SHORT_LABELS,
    STATUSES,
    coverage,
    markdown,
    unreviewed,
    unreviewed_markdown,
    upstream,
)
from codemeta_drift.export import (
    FORMATS,
    KINDS,
    NO_PROPERTY,
    PACKAGE,
    TERMS,
    build_rows,
    curated_tags,
    latest_tag,
    read_curated,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(params=curated_tags())
def example(request: pytest.FixtureRequest) -> Path:
    return ROOT / f"examples/mapping-{request.param}.json"


@pytest.fixture
def mapping(example: Path):
    return json.loads(example.read_text("utf-8"))


@pytest.fixture
def tag_files(mapping: dict) -> Path:
    return ROOT / "tests/fixtures" / mapping["codemeta_tag"]


def statuses(mapping: dict):
    return {(c["format"], c["term"]): c["status"] for c in coverage(mapping)["cells"]}


def test_coverage_index_links_every_tag():
    index = (ROOT / "docs/coverage.md").read_text("utf-8")
    assert all(f"(coverage-{tag}.md)" in index for tag in curated_tags())


def test_coverage_index_counts_match_the_newest_export():
    rows = json.loads((ROOT / f"examples/mapping-{latest_tag()}.json").read_text("utf-8"))["rows"]
    formats = {r["format"] for r in rows}
    shown = formats - {"codemeta"}
    no_crosswalk = {f for f in shown if FORMATS[f].crosswalk is None}
    index = " ".join((ROOT / "docs/coverage.md").read_text("utf-8").split())
    assert f"The page shows {len(shown)} of the export's {len(formats)} formats" in index
    assert f"{len(no_crosswalk)} of them with no CodeMeta crosswalk" in index
    assert f"The page's filters count all {sum(r['format'] in shown for r in rows)} cells" in index


@pytest.mark.parametrize("tag", curated_tags())
def test_docs_page_is_generated_from_the_example(tag: str):
    # Regenerate as docs/development.md says, with a CodeMeta clone that has the tag.
    example = json.loads((ROOT / f"examples/mapping-{tag}.json").read_text("utf-8"))
    page = (ROOT / f"docs/coverage-{tag}.md").read_text("utf-8")
    assert page == markdown(example, read_dir(ROOT / "tests/fixtures" / tag))
    # The citation columns come from the reviewed rows, not CodeMeta's crosswalks.
    n = len(coverage(example)["terms"])
    assert f"How CodeMeta's {tag} crosswalks and the reviewed citation fields map {n} terms in " in page


def test_unreviewed_lists_every_other_crosswalk_by_shape(mapping: dict, tag_files: Path):
    data = unreviewed(read_dir(tag_files), mapping)
    names = [f["format"] for f in data["formats"]]
    assert len(names) == 10  # both pinned tags leave the same crosswalks unreviewed
    assert "Zenodo" not in names
    assert "NodeJS" not in names
    found = {(c["format"], c["term"]): c["status"] for c in data["cells"]}
    assert len(found) == 10 * 19
    assert found["ASCL", "name"] == "path"
    assert found["DCAT", "name"] == "path"  # dcterms:title, a prefixed key since schema 1.6
    assert found["csdms", "description"] == "prose"
    assert found["ASCL", "version"] == "empty"
    assert {s for (_, term), s in found.items() if term == "resourceType"} == {"no-term"}
    assert {f["label"] for f in data["formats"] if f["format"] == "DCAT"} == {"DCAT-2"}


def test_every_status_names_an_unreviewed_crosswalk(mapping: dict, tag_files: Path):
    """A crosswalk that gets reviewed leaves NOT_REVIEWED, so no stale reason stays on the page."""
    formats = {f["format"]: f for f in unreviewed(read_dir(tag_files), mapping)["formats"]}
    assert NOT_REVIEWED.keys() <= formats.keys()
    for name, (status, reason, url) in NOT_REVIEWED.items():
        assert status in {"superseded", "registry", "niche"}
        assert (formats[name]["status"], formats[name]["reason"], formats[name]["url"]) == (status, reason, url)


def test_unreviewed_marks_a_cell_it_cannot_join(mapping: dict, tag_files: Path):
    files = read_dir(tag_files)
    ascl = "crosswalks/ASCL.csv"
    files[ascl] = files[ascl].replace("\nversion,", "\nversion,\nversion,", 1)
    found = {(c["format"], c["term"]): c["status"] for c in unreviewed(files, mapping)["cells"]}
    assert found["ASCL", "version"] == "unmatched"


def test_a_format_the_mapping_lacks_counts_as_not_reviewed(mapping: dict, tag_files: Path):
    partial = mapping
    partial["rows"] = [row for row in partial["rows"] if row["format"] != "bibtex"]
    assert "bibtex" not in coverage(partial)["formats"]
    files = read_dir(tag_files)
    assert "BibTeX" in [f["format"] for f in unreviewed(files, partial)["formats"]]
    assert "| bibtex |" not in markdown(partial, files)


def test_cli_lists_unreviewed_crosswalks_from_the_tag(example: Path, repo: Path, capsys: pytest.CaptureFixture[str]):
    assert main(["hub", "coverage", str(example), "--json", "--codemeta", str(repo)]) == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data["unreviewed"]["formats"]) == 10


def test_cli_coverage_without_the_tag_exits_3(example: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    assert main(["hub", "coverage", str(example), "--codemeta", str(tmp_path)]) == 3
    assert capsys.readouterr().err.startswith(f"codemeta-drift: cannot read {tmp_path}: fatal:")


def test_known_cells_get_their_status(mapping: dict):
    found = statuses(mapping)
    assert found["cff-1.2.0", "name"] == "as-is"
    assert found["cargo", "name"] == "corrected"  # the cell says package.authors
    assert found["npm", "identifier"] == "scope"  # the cell says name, an identifier but not a DOI
    assert found["npm", "swhid"] == "scope"  # the same cell, read again for the hub's own swhid term
    assert found["zenodo", "author.@id"] == "notation"  # the cell says ORCID, the key is orcid
    assert found["cargo", "description"] == "added"  # no cell, though Cargo has package.description
    assert found["cargo", "datePublished"] == "no field"
    # The contributor person rows reuse the Person cells, but CFF has no contributor list to hold them.
    assert found["cff-1.2.0", "contributor.givenName"] == "no field"
    assert found["cff-1.2.0", "author.givenName"] == "as-is"  # the same Person row, with an author list
    assert found["pep621", "contributor.@id"] == "no field"
    assert not any(fmt == "codemeta" for fmt, _ in found)


def test_every_kind_marks_a_cell_that_would_be_corrected(mapping: dict):
    """A kind on a row the crosswalk reads, or on an added cell, would be dropped without a word."""
    tag = mapping["codemeta_tag"]
    found = statuses(mapping)
    kinds = {(r["format"], r["term"]): r["kind"] for r in read_curated(tag) if "kind" in r}
    assert kinds
    assert {key: found[key] for key in kinds} == kinds


def test_kind_comes_from_the_mapping_row(mapping: dict):
    """A hand-edited export or one from another release gets the statuses its own rows say."""
    row = next(r for r in mapping["rows"] if (r["format"], r["term"]) == ("zenodo", "author.@id"))
    assert row.pop("kind", None) == "notation"
    assert statuses(mapping)["zenodo", "author.@id"] == "corrected"


def test_an_unknown_kind_is_refused():
    with pytest.raises(ValueError, match="row 1 has kind 'typo'"):
        build_rows({}, "4.0", [{"format": "cargo", "term": "name", "path": "x", "reason": "r", "kind": "typo"}])


def test_an_unknown_kind_message_lists_the_kinds():
    with pytest.raises(ValueError, match=r"not one of notation, scope$"):
        build_rows({}, "4.0", [{"format": "cargo", "term": "name", "path": "x", "reason": "r", "kind": "typo"}])


def test_a_kind_on_a_cell_the_crosswalk_leaves_empty_is_refused():
    """status() reads a kind only off a non-empty cell, so the coverage page would show it as added."""
    files = read_dir(ROOT / "tests/fixtures/4.0")
    row = {"format": "cargo", "term": "description", "path": "package.description", "cell": "", "reason": "r"}
    with pytest.raises(
        ValueError, match=r"^curated-4\.0\.json: the cargo description row has kind 'scope', but its cell is empty$"
    ):
        build_rows(files, "4.0", [row | {"kind": "scope"}])


def test_the_kind_vocabulary_is_spelled_the_same_everywhere():
    schema = json.loads((PACKAGE / "mapping.schema.json").read_text("utf-8"))
    assert list(KINDS) == schema["$defs"]["row"]["properties"]["kind"]["enum"]
    assert set(KINDS) <= STATUSES.keys()


def test_a_scope_cell_with_no_path_is_one_the_meaning_admits(mapping: dict):
    """Half the scope cells have no narrow field in the format; the meaning must not promise a path."""
    cells = coverage(mapping)["cells"]
    assert any(c["status"] == "scope" and c["path"] is None for c in cells)
    assert STATUSES["scope"][1].endswith("the reviewed mapping gives the path, or says the format has none")


def test_counts_for_the_crosswalks(mapping: dict):
    found = [c["status"] for c in coverage(mapping)["cells"] if c["crosswalk"]]
    expected = {
        "3.1": {
            "as-is": 115,
            "scope": 40,
            "notation": 80,
            "corrected": 74,
            "added": 110,
            "no field": 219,
            "no term": 11,
        },
        "4.0": {
            "as-is": 124,
            "scope": 42,
            "notation": 80,
            "corrected": 82,
            "added": 111,
            "no field": 237,
            "no term": 11,
        },
    }
    assert {s: found.count(s) for s in set(found)} == expected[mapping["codemeta_tag"]]


def test_readme_figures_match_the_counts():
    mapping = json.loads((ROOT / f"examples/mapping-{latest_tag()}.json").read_text("utf-8"))
    # The README counts the base terms but resourceType, which has no CodeMeta property row for a cell.
    cells = [
        c for c in coverage(mapping)["cells"] if c["crosswalk"] and c["term"] in TERMS and c["term"] not in NO_PROPERTY
    ]
    count = Counter(c["status"] for c in cells)
    null_corrected = sum(c["status"] == "corrected" and c["path"] is None for c in cells)
    text = " ".join((ROOT / "README.md").read_text("utf-8").split())
    terms = len(TERMS) - len(NO_PROPERTY)
    assert (
        f"for the {terms} terms citation tools need. That gives {len(cells)} cells, one per crosswalk and term:"
        f" - {count['as-is']} can be used as written."
        f" - {count['notation']} name the right field in a form a tool can't use as a path,"
        f" such as another case, no prefix or XPath."
        f" - {count['scope']} are right by CodeMeta's definition, but codemeta-drift reads the term more narrowly,"
        f" such as `identifier` as the software's DOI and `swhid` as a term of its own, or also reads another field,"
        f" such as a fallback or a newer one. The reviewed mapping gives the path, or says the format has none."
        f" - {count['corrected']} are wrong, ambiguous or prose."
        f" {null_corrected} of them name a field the format doesn't have."
        f" - {count['added']} are blank although the format has the field."
        f" - {count['no field']} are for a term the format has no field for."
    ) in text


def test_format_lists_and_counts_match_the_export():
    order = ", ".join(f"`{f}`" for f in FORMATS)
    guide = " ".join((ROOT / "docs/mapping-export.md").read_text("utf-8").split())
    assert f"in the order {order}, and within a format" in guide
    schema = json.loads((ROOT / "src/codemeta_drift/mapping.schema.json").read_text("utf-8"))
    described = schema["$defs"]["row"]["properties"]["format"]["description"]
    assert ", ".join(FORMATS) in described
    mapping = json.loads((ROOT / f"examples/mapping-{latest_tag()}.json").read_text("utf-8"))
    n = len({r["format"] for r in mapping["rows"]})
    for doc in ("README.md", "docs/crosswalk-hub.md"):
        assert f"{n} formats" in " ".join((ROOT / doc).read_text("utf-8").split()), doc


def test_cli_writes_json(mapping: dict, example: Path, capsys: pytest.CaptureFixture[str]):
    assert main(["hub", "coverage", str(example), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["codemeta_tag"] == mapping["codemeta_tag"]
    assert len(data["cells"]) == {"3.1": 879, "4.0": 917}[mapping["codemeta_tag"]]
    assert "unreviewed" not in data  # only with --codemeta


def test_upstream_reports_unmatched_changed_and_fixed_cells(mapping: dict, tag_files: Path):
    files = read_dir(tag_files)
    assert upstream(files, mapping) == []
    cargo = "crosswalks/Cargo.csv"
    files[cargo] = files[cargo].replace("keywords,package.keyword", "keywords,package.keywords")
    files[cargo] = files[cargo].replace("version,package.version", "version,package.ver")
    zenodo = "crosswalks/Zenodo.csv"
    files[zenodo] = files[zenodo].replace("\nversion,", "\nversion,\nversion,", 1)
    cff = "crosswalks/Citation File Format 1.2.0.csv"
    files[cff] = files[cff].replace("\nname,title", "\nname,name", 1)
    found = {(c["format"], c["term"]): c["state"] for c in upstream(files, mapping)}
    assert found == {
        ("cargo", "keywords"): "fixed",
        ("cargo", "version"): "changed",
        ("zenodo", "version"): "unmatched",
        ("cff-1.2.0", "name"): "changed",  # an as-is cell that changes is never "fixed"
    }


def test_a_citation_cell_that_gives_the_path_is_changed_not_fixed(mapping: dict, tag_files: Path):
    files = read_dir(tag_files)
    datacite = "crosswalks/DataCite.csv"
    assert "\nurl,\n" in files[datacite]
    files[datacite] = files[datacite].replace("\nurl,\n", "\nurl,url\n", 1)
    cargo = "crosswalks/Cargo.csv"
    files[cargo] = files[cargo].replace("keywords,package.keyword", "keywords,package.keywords")
    found = {(c["format"], c["term"]): c["state"] for c in upstream(files, mapping)}
    # The curated row is what exports a citation term, so it can never go.
    assert found == {("datacite", "url"): "changed", ("cargo", "keywords"): "fixed"}


@pytest.mark.parametrize(
    ("cell", "term"),
    [
        ("identifier,ORCID", "author.@id"),  # Zenodo: orcid derives to creators[].orcid
        ("identifier,ORCID", "contributor.@id"),
    ],
)
def test_upstream_derives_the_new_cell_before_calling_it_fixed(mapping: dict, tag_files: Path, cell: str, term: str):
    files = read_dir(tag_files)
    zenodo = "crosswalks/Zenodo.csv"
    assert cell in files[zenodo]
    files[zenodo] = files[zenodo].replace(cell, "identifier,orcid")
    found = {(c["format"], c["term"]): c["state"] for c in upstream(files, mapping)}
    assert found["zenodo", term] == "fixed"


def test_an_emptied_cell_is_not_a_fix_for_a_format_with_no_field(mapping: dict, tag_files: Path):
    files = read_dir(tag_files)
    npm = "crosswalks/NodeJS.csv"
    assert "\nidentifier,name" in files[npm]
    files[npm] = files[npm].replace("\nidentifier,name", "\nidentifier,", 1)
    found = {(c["format"], c["term"]): c["state"] for c in upstream(files, mapping)}
    # The export would refuse that empty cell without its curated row, so the row must stay.
    assert found["npm", "identifier"] == "changed"


def test_upstream_says_missing_when_a_crosswalk_is_gone(mapping: dict, tag_files: Path):
    files = read_dir(tag_files)
    del files["crosswalks/Cargo.csv"]
    states = {c["state"] for c in upstream(files, mapping) if c["format"] == "cargo"}
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
def test_a_url_in_a_reason_is_shown_as_code(mapping: dict, reason: str, shown: str):
    data = mapping
    row = next(r for r in data["rows"] if r["format"] == "cargo" and r["source"].startswith("curated:"))
    row["source"] = f"curated:{reason}"
    assert shown in markdown(data)


def test_no_crosswalk_sentence_needs_a_format_without_one(mapping: dict):
    mapping["rows"] = [r for r in mapping["rows"] if FORMATS[r["format"]].crosswalk]
    page = markdown(mapping)
    assert "have no CodeMeta crosswalk" not in page
    assert "(mapping-export.md). The [web page]" in page


def test_a_backtick_in_a_crosswalk_cell_keeps_the_code_span_closed(mapping: dict):
    row = next(r for r in mapping["rows"] if r["source"].startswith("curated:"))
    row["crosswalk_cell"] = "a`@x "
    assert "crosswalk cell ``a`@x`` →" in markdown(mapping)


def test_coverage_report_keys(mapping: dict):
    """The site reads these keys by name."""
    data = coverage(mapping)
    assert list(data) == ["codemeta_tag", "generator", "formats", "terms", "statuses", "cells"]
    assert (data["codemeta_tag"], data["generator"]) == (mapping["codemeta_tag"], mapping["generator"])
    assert data["statuses"] == {name: {"mark": mark, "meaning": text} for name, (mark, text) in STATUSES.items()}


def test_unreviewed_report_keys(mapping: dict, tag_files: Path):
    data = unreviewed(read_dir(tag_files), mapping)
    assert list(data) == ["codemeta_tag", "statuses", "formats", "cells"]
    assert data["codemeta_tag"] == mapping["codemeta_tag"]
    assert data["statuses"] == {name: {"mark": mark, "meaning": text} for name, (mark, text) in SHAPES.items()}
    assert all(list(f) == ["format", "label", "crosswalk", "status", "reason", "url"] for f in data["formats"])
    assert all(f["crosswalk"] == f"crosswalks/{f['format']}.csv" for f in data["formats"])
    keys = ["format", "term", "status", "path", "cell", "crosswalk", "reason"]
    assert all(list(c) == keys for c in data["cells"])
    assert all(c["path"] is None and c["reason"] is None for c in data["cells"])
    assert all(c["crosswalk"] == f"crosswalks/{c['format']}.csv" for c in data["cells"])
    assert any(c["cell"] for c in data["cells"])
    # Perl's crosswalk is reviewed, so only a mapping without its rows shows its short label.
    mapping["rows"] = [row for row in mapping["rows"] if row["format"] != "cpan-meta-2"]
    labels = {f["format"]: f["label"] for f in unreviewed(read_dir(tag_files), mapping)["formats"]}
    assert {fmt: labels[fmt] for fmt in SHORT_LABELS} == SHORT_LABELS


def test_a_bar_in_an_unreviewed_label_keeps_the_table_row(mapping: dict, tag_files: Path):
    data = unreviewed(read_dir(tag_files), mapping)
    data["formats"][0]["label"] = "a|b"
    assert any(line.startswith("| a\\|b | ") for line in unreviewed_markdown(data, list(TERMS)))


def test_a_missing_row_leaves_only_its_cell_empty(mapping: dict):
    first, second = list(TERMS)[:2]
    mapping["rows"] = [r for r in mapping["rows"] if (r["format"], r["term"]) != ("cargo", first)]
    keys = {(c["format"], c["term"]) for c in coverage(mapping)["cells"]}
    assert ("cargo", first) not in keys
    assert ("cargo", second) in keys
    formats = coverage(mapping)["formats"]
    [line] = [x for x in markdown(mapping).splitlines() if x.startswith((f"| `{first}` |", f"| {first} |"))]
    cells = [c.strip() for c in re.split(r"(?<!\\)\|", line)[1:-1]]
    assert len(cells) == len(formats) + 1
    assert cells[1 + formats.index("cargo")] == ""


def test_a_reason_ends_in_one_full_stop(mapping: dict):
    row = next(r for r in mapping["rows"] if r["source"].startswith("curated:"))
    row["source"] = "curated:a.b, then a stop at X."
    assert f"`{row['term']}` (" in markdown(mapping)
    assert any(line.endswith(" A.b, then a stop at X.") for line in markdown(mapping).splitlines())


def test_upstream_gives_each_cell_its_new_text(mapping: dict, tag_files: Path):
    files = read_dir(tag_files)
    cargo = "crosswalks/Cargo.csv"
    files[cargo] = files[cargo].replace("keywords,package.keyword", "keywords,package.keywords")
    [cell] = upstream(files, mapping)
    assert (cell["now"], cell["state"]) == ("package.keywords", "fixed")
    del files["crosswalks/Zenodo.csv"]
    changed = upstream(files, mapping)
    missing = [c for c in changed if c["state"] == "missing"]
    assert {c["format"] for c in missing} == {"zenodo"}
    assert len(missing) == len([c for c in coverage(mapping)["cells"] if c["format"] == "zenodo"])
    assert all(c["now"] is None for c in missing)
    assert ("cargo", "keywords") in {(c["format"], c["term"]) for c in changed}


def test_an_as_is_cell_rewritten_as_its_own_path_is_not_a_fix(mapping: dict, tag_files: Path):
    """CFF's person.given-names derives to authors[].given-names; the new text is that path, still as-is."""
    files = read_dir(tag_files)
    cff = "crosswalks/Citation File Format 1.2.0.csv"
    files[cff] = files[cff].replace("\ngivenName,person.given-names", "\ngivenName,authors[].given-names", 1)
    found = {(c["format"], c["term"]): c["state"] for c in upstream(files, mapping)}
    assert found["cff-1.2.0", "author.givenName"] == "changed"


def test_a_person_cell_for_a_list_the_format_lacks_is_never_a_fix(mapping: dict, tag_files: Path):
    """CFF has no contributor list, so its contributor.givenName path is None, as derive() gives here."""
    files = read_dir(tag_files)
    cff = "crosswalks/Citation File Format 1.2.0.csv"
    files[cff] = files[cff].replace("\ngivenName,person.given-names", "\ngivenName,person.first-name", 1)
    found = {(c["format"], c["term"]): c["state"] for c in upstream(files, mapping)}
    assert found["cff-1.2.0", "contributor.givenName"] == "changed"
