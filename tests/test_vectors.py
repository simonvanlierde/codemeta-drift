"""The grammar vectors: each path fits the grammar, and resolves to the listed values in its document."""

import json
import re
import xml.etree.ElementTree as ET
from importlib import resources
from pathlib import Path
from typing import Any

import pytest

from codemeta_drift.export import PATH
from codemeta_drift.paths import resolve

PACKAGE = resources.files("codemeta_drift")
ROOT = Path(__file__).resolve().parents[1]
VECTORS = json.loads(PACKAGE.joinpath("mapping-vectors.json").read_text("utf-8"))
CASES = VECTORS["cases"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
def test_vector_path_is_in_the_grammar(case: dict) -> None:
    assert PATH.fullmatch(case["path"])


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
def test_vector_resolves(case: dict) -> None:
    assert resolve(case["document"], case["path"]) == case["expected"]


def test_vectors_cover_each_form() -> None:
    paths = " ".join(c["path"] for c in CASES)
    for form in (" | ", " + ", "[]", "[type=", "@url", "Authors@R", "dcterms:", ".url", "[@id=./]"):
        assert form in paths


@pytest.mark.parametrize(
    "case", [c for c in CASES if "parser" in c["name"] and "Author" in c["name"]], ids=lambda c: c["name"]
)
def test_pkg_info_parser_vectors_include_raw_headers(case: dict) -> None:
    assert case["raw_input"]["format"] == "pkg-info"
    assert case["raw_input"]["text"].startswith(("Author: ", "Author-email: "))
    assert case["raw_input"]["text"].endswith("\n")


# The lists rule of docs/mapping-export.md for RO-Crate and Croissant: these keys are read as lists.
LISTED = ("author", "creator", "contributor", "identifier", "license", "publisher")


def read_json_ld(fmt: str, text: str) -> dict:
    """A crate or Croissant file read as docs/mapping-export.md says: references replaced, bare values listed."""
    tree = json.loads(text)
    root = tree
    if fmt == "ro-crate":
        entities = {e["@id"]: e for e in tree["@graph"]}
        root = next(e for e in tree["@graph"] if e["@id"] == "./")

        def entity(value: object) -> object:
            is_ref = isinstance(value, dict) and value.keys() == {"@id"}
            return entities.get(value["@id"], value) if is_ref else value

        for key, value in root.items():
            root[key] = [entity(v) for v in value] if isinstance(value, list) else entity(value)
    for key in LISTED:
        if key in root and not isinstance(root[key], list):
            root[key] = [root[key]]
    return tree


JSON_LD = {
    c["raw_input"]["format"]: c for c in CASES if c.get("raw_input", {}).get("format") in ("ro-crate", "croissant")
}


@pytest.mark.parametrize("fmt", ["ro-crate", "croissant"])
def test_json_ld_parser_vectors_match_the_reading_rules(fmt: str) -> None:
    case = JSON_LD[fmt]
    assert read_json_ld(fmt, case["raw_input"]["text"]) == case["document"]


# What each non-null curated row reads from the parser vectors' documents.
EXPECTED = {
    "name": ["Carberry's lab notes"],
    "version": ["1.2.0"],
    "author.givenName": ["Josiah"],
    "author.familyName": ["Carberry"],
    "author.@id": ["https://orcid.org/0000-0002-1825-0097"],
    "license": ["https://spdx.org/licenses/MIT"],
    "description": ["Readings from the psychoceramics lab."],
    "datePublished": ["2026-11-10"],
    "publisher": ["Psychoceramics Society"],
    "contributor.givenName": ["Ada"],
    "contributor.familyName": ["Lovelace"],
}


@pytest.mark.parametrize("tag", ["3.1", "4.0"])
@pytest.mark.parametrize("fmt", ["ro-crate", "croissant"])
def test_curated_json_ld_rows_read_the_vector_documents(fmt: str, tag: str) -> None:
    rows = json.loads(PACKAGE.joinpath(f"curated-{tag}.json").read_text("utf-8"))["rows"]
    paths = {r["term"]: r["path"] for r in rows if r["format"] == fmt}
    document = JSON_LD[fmt]["document"]
    for term, values in EXPECTED.items():
        assert resolve(document, paths[term]) == values, term
    assert [a["name"] for a in resolve(document, paths["author"])] == ["Josiah Carberry"]
    doi = "https://doi.org/10.5555/carberry.notes"
    identifier = {"ro-crate": [doi, "doi:10.5555/carberry.notes", doi], "croissant": [doi]}
    # The path also returns the identifier objects themselves; the consumer skips them.
    assert [v for v in resolve(document, paths["identifier"]) if isinstance(v, str)] == identifier[fmt]
    keywords = {"ro-crate": ["ceramics, cracks"], "croissant": [["ceramics", "cracks"]]}
    assert resolve(document, paths["keywords"]) == keywords[fmt]
    resource_type = {"ro-crate": ["Dataset"], "croissant": ["sc:Dataset"]}
    assert resolve(document, paths["resourceType"]) == resource_type[fmt]
    assert [c["name"] for c in resolve(document, paths["contributor"])] == ["Ada Lovelace"]
    assert resolve(document, paths["contributor.@id"]) == {"ro-crate": ["#contributor-1"], "croissant": []}[fmt]


@pytest.mark.parametrize("tag", ["3.1", "4.0"])
@pytest.mark.parametrize("fmt", ["ro-crate", "croissant"])
def test_curated_identifier_keeps_a_string_doi_after_an_object(fmt: str, tag: str) -> None:
    rows = json.loads(PACKAGE.joinpath(f"curated-{tag}.json").read_text("utf-8"))["rows"]
    path = next(r["path"] for r in rows if r["format"] == fmt and r["term"] == "identifier")
    ids = [{"@id": "#isbn", "@type": "PropertyValue", "value": "978-0-306-40615-7"}, "https://doi.org/10.5555/x"]
    document = {"@graph": [{"@id": "./", "identifier": ids}]} if fmt == "ro-crate" else {"identifier": ids}
    assert "https://doi.org/10.5555/x" in resolve(document, path)


def curated_paths(tag: str, fmt: str) -> dict[str, Any]:
    rows = json.loads(PACKAGE.joinpath(f"curated-{tag}.json").read_text("utf-8"))["rows"]
    return {r["term"]: r["path"] for r in rows if r["format"] == fmt}


def raw_case(fmt: str) -> dict:
    return next(c for c in CASES if c.get("raw_input", {}).get("format") == fmt)


def read_oai_dc(text: str) -> dict:
    """An oai_dc record read as docs/mapping-export.md says: each element a dc: key, every key a list."""
    tree: dict[str, list[str]] = {}
    for child in ET.fromstring(text):  # noqa: S314 - the vectors ship in this package
        tree.setdefault(f"dc:{child.tag.rpartition('}')[2]}", []).append((child.text or "").strip())
    return tree


def test_oai_dc_parser_vector_matches_the_reading_rules() -> None:
    case = raw_case("oai_dc")
    assert read_oai_dc(case["raw_input"]["text"]) == case["document"]


@pytest.mark.parametrize("tag", ["3.1", "4.0"])
def test_curated_dublin_core_rows_read_both_carriers(tag: str) -> None:
    paths = curated_paths(tag, "dublin-core")
    oai = raw_case("oai_dc")["document"]
    rdf = next(c for c in CASES if c["name"].startswith("Dublin Core: a dcterms record"))["document"]
    people = ["van Leeuwenhoek, Antonie", "Skłodowska-Curie, Marie"]
    expected = {
        "name": (["Animalcule Counter"], ["Animalcule Counter"]),
        "author": (people, rdf["dcterms:creator"]),
        "author.givenName": (people, ["Josiah"]),
        "author.familyName": (people, ["Carberry"]),
        "author.@id": ([], ["https://orcid.org/0000-0002-1825-0097"]),
        "contributor": (["Hua, Luogeng"], rdf["dcterms:contributor"]),
        "contributor.givenName": (["Hua, Luogeng"], ["Luogeng"]),
        "contributor.familyName": (["Hua, Luogeng"], ["Hua"]),
        "contributor.@id": ([], []),
        "license": (oai["dc:rights"], [{"@id": "https://spdx.org/licenses/MIT.html"}]),
        "identifier": (oai["dc:identifier"], ["https://doi.org/10.5555/example.1234"]),
        "description": (["Counts animalcules in microscope images."], []),
        "keywords": (["microscopy", "image analysis"], []),
        "datePublished": (["2026-03-14"], [rdf["dcterms:issued"]]),
        "publisher": (["Example Lab"], ["Example Lab"]),
        "resourceType": (["Software"], [{"@id": "http://purl.org/dc/dcmitype/Software"}]),
    }
    for term, (from_oai, from_rdf) in expected.items():
        assert resolve(oai, paths[term]) == from_oai, term
        assert resolve(rdf, paths[term]) == from_rdf, term
    nulls = {t for t, p in paths.items() if p is None}
    assert nulls == {"version", "swhid", "codeRepository"}
    assert set(expected) | nulls == set(paths)


def read_deb822(text: str) -> list[dict[str, str]]:
    """deb822 stanzas as docs/mapping-export.md reads them: names in Policy's spelling, continuations kept."""
    stanzas = []
    for block in re.split(r"\n\s*\n", text.strip("\n")):
        stanza: dict[str, str] = {}
        key = ""
        for line in block.splitlines():
            if line[:1] in (" ", "\t"):
                stanza[key] += "\n" + line[1:]
            else:
                name, _, value = line.partition(":")
                key = "-".join(part.capitalize() for part in name.split("-"))
                stanza[key] = value.strip()
        stanzas.append(stanza)
    return stanzas


def test_debian_control_parser_vector_matches_the_reading_rules() -> None:
    case = raw_case("debian-control")
    control, *packages = read_deb822(case["raw_input"]["text"])
    assert {"control": control, "packages": packages} == case["document"]


DEBIAN_COPYRIGHT = """\
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: carberry
Upstream-Contact: Josiah Carberry <josiah@example.org>
Source: https://carberry.example.org/releases/
License: Expat
"""
DEBIAN_CHANGELOG = "python-carberry (1:2.4.0-1) unstable; urgency=medium"
DEBIAN_UPSTREAM = """\
Bug-Database: https://git.example.org/carberry/carberry/issues
Repository: https://git.example.org/carberry/carberry.git
Repository-Browse: https://git.example.org/carberry/carberry
"""


@pytest.mark.parametrize("tag", ["3.1", "4.0"])
def test_curated_debian_rows_read_the_source_tree(tag: str) -> None:
    paths = curated_paths(tag, "debian")
    version = re.match(r"\S+ \((\S+)\)", DEBIAN_CHANGELOG)
    assert version
    upstream = dict(line.partition(": ")[::2] for line in DEBIAN_UPSTREAM.splitlines())
    tree = {
        **raw_case("debian-control")["document"],
        "copyright": read_deb822(DEBIAN_COPYRIGHT)[0],
        "changelog": {"Version": version[1]},
        "upstream": upstream,
    }
    assert resolve(tree, paths["name"]) == ["carberry"]
    assert resolve(tree, paths["version"]) == ["1:2.4.0-1"]
    assert resolve(tree, paths["license"]) == ["Expat"]
    assert resolve(tree, paths["codeRepository"]) == ["https://git.example.org/carberry/carberry.git"]
    assert resolve({k: v for k, v in tree.items() if k != "upstream"}, paths["codeRepository"]) == [
        "https://carberry.example.org/"
    ]
    [description] = resolve(tree, paths["description"])
    assert description.startswith("lab notes for psychoceramics research\n")
    assert {t for t, p in paths.items() if p is not None} == {
        "name",
        "version",
        "license",
        "codeRepository",
        "description",
    }


def read_xml(node: ET.Element) -> Any:  # noqa: ANN401 - a string or a tree
    """An XML element as docs/mapping-export.md reads MODS: each child a list, attributes @ keys, text in #text."""
    tree: dict[str, Any] = {
        "@" + key.replace("{http://www.w3.org/1999/xlink}", "xlink:"): value
        for key, value in node.attrib.items()
        if not key.startswith("{http://www.w3.org/2001/XMLSchema-instance}")
    }
    for child in node:
        tree.setdefault(child.tag.rpartition("}")[2], []).append(read_xml(child))
    if len(node):
        return tree
    text = (node.text or "").strip()
    return {**tree, "#text": text} if tree else text


def read_mods(text: str) -> dict:
    """The first mods record, with each name's role.roleTerm texts lifted into a roleTerm list."""
    root = ET.fromstring(text.encode())  # noqa: S314 - the vectors ship in this package
    record = read_xml(next(root.iter("{http://www.loc.gov/mods/v3}mods")))
    for name in record.get("name", []):
        terms = [term for role in name.get("role", []) for term in role.get("roleTerm", [])]
        name["roleTerm"] = [term["#text"] if isinstance(term, dict) else term for term in terms]
    return record


def text_of(values: list) -> list:
    """What a consumer takes from each value: an element with attributes gives its #text."""
    return [v["#text"] if isinstance(v, dict) and "#text" in v else v for v in values]


def test_mods_parser_vector_matches_the_reading_rules() -> None:
    case = raw_case("mods")
    assert read_mods(case["raw_input"]["text"]) == case["document"]


@pytest.mark.parametrize("tag", ["3.1", "4.0"])
def test_curated_mods_rows_read_the_vector_document(tag: str) -> None:
    paths = curated_paths(tag, "mods")
    document = raw_case("mods")["document"]
    expected = {
        "name": ["tidewater", "Tidewater toolkit"],
        "version": ["2.1.0"],
        "author.givenName": ["Ada"],
        "author.familyName": ["Lovelace"],
        "author.@id": ["https://orcid.org/0000-0002-1825-0097"],
        "contributor.givenName": ["Grace"],
        "contributor.familyName": ["Hopper"],
        "contributor.@id": [],
        "license": ["MIT License"],
        "identifier": ["10.5281/zenodo.1234567"],
        "description": ["Cleans and resamples tide-gauge records for coastal models."],
        "keywords": ["oceanography", "time series"],
        "datePublished": ["2024-03-14"],
        "publisher": ["Zenodo"],
        "resourceType": ["software, multimedia"],
    }
    for term, values in expected.items():
        assert text_of(resolve(document, paths[term])) == values, term
    assert [p["#text"] for a in resolve(document, paths["author"]) for p in a["namePart"]] == ["Ada", "Lovelace"]
    assert [p["#text"] for c in resolve(document, paths["contributor"]) for p in c["namePart"]] == ["Grace", "Hopper"]
    assert resolve(document, paths["license"])[0]["@xlink:href"] == "https://spdx.org/licenses/MIT.html"


@pytest.mark.parametrize("tag", ["3.1", "4.0"])
def test_curated_vivo_rows_read_the_framed_graph(tag: str) -> None:
    # The suite has no RDF parser: the vector's document is the framing pyld and rdflib give its Turtle.
    paths = curated_paths(tag, "vivo-1.8")
    document = raw_case("vivo")["document"]
    expected = {
        "name": ["Animalcule Counter"],
        "version": ["2.1.0"],
        "author.givenName": ["Antonie", "Luogeng"],
        "author.familyName": ["van Leeuwenhoek", "Hua"],
        "author.@id": ["https://orcid.org/0000-0002-1825-0097"],
        "identifier": ["10.5555/animalcule.2.1.0"],
        "swhid": ["swh:1:dir:d198bc9d7a6bcf6db04f476d29314f157507d505"],
        "description": ["Counts animalcules in microscope images."],
        "keywords": [["microscopy", "image analysis"]],
        "publisher": ["Carberry Institute"],
        "resourceType": ["obo:ERO_0000071"],
    }
    for term, values in expected.items():
        assert resolve(document, paths[term]) == values, term
    # Ranked: the first Authorship is rank 1, though the graph lists it second.
    assert [a["rdfs:label"] for a in resolve(document, paths["author"])] == ["van Leeuwenhoek, Antonie", "Hua, Luogeng"]
    assert [d["@value"] for d in resolve(document, paths["datePublished"])] == ["2025-03-14T00:00:00"]


SPASE_LISTS = {"AccessInformation", "AccessURL", "Contact", "Role"}
"""The elements of the vector record that the SPASE schema lets repeat, so the reading rule lists them."""


def read_spase(node: ET.Element) -> Any:  # noqa: ANN401 - a string or a tree
    if not len(node):
        return (node.text or "").strip()
    tree: dict[str, Any] = {}
    for child in node:
        key = child.tag.rpartition("}")[2]
        if key in SPASE_LISTS:
            tree.setdefault(key, []).append(read_spase(child))
        else:
            tree[key] = read_spase(child)
    return tree


def test_spase_parser_vector_matches_the_reading_rules() -> None:
    case = raw_case("spase")
    root = ET.fromstring(case["raw_input"]["text"].encode())  # noqa: S314 - the vectors ship in this package
    assert read_spase(next(root.iter("{http://www.spase-group.org/data/schema}Software"))) == case["document"]


@pytest.mark.parametrize("tag", ["3.1", "4.0"])
def test_curated_spase_rows_read_the_vector_document(tag: str) -> None:
    paths = curated_paths(tag, "spase-2.6.1")
    document = raw_case("spase")["document"]
    authors = ["Lovelace, Ada; Hopper, Grace Brewster"]
    expected = {
        "name": ["fern-spectra"],
        "version": ["1.4.0"],
        "author": authors,
        "author.givenName": authors,
        "author.familyName": authors,
        "contributor": [{"PersonID": "spase://SMWG/Person/Alan.Turing", "Role": ["Contributor"]}],
        "identifier": ["https://doi.org/10.5281/zenodo.1234567"],
        "codeRepository": ["https://github.com/example/fern-spectra"],
        "description": ["Fits and plots auroral emission spectra from all-sky camera frames."],
        "datePublished": ["2026-02-27T00:00:00Z"],
        "publisher": ["Zenodo"],
    }
    assert {t: resolve(document, p) for t, p in paths.items() if p is not None} == expected


ISO_LISTS = {
    "MD_Metadata": {"metadataScope", "contact", "dateInfo"},
    "MD_DataIdentification": {"descriptiveKeywords", "resourceConstraints"},
    "CI_Citation": {"date", "identifier", "citedResponsibleParty", "onlineResource"},
    "CI_Responsibility": {"party"},
    "CI_Individual": {"contactInfo", "partyIdentifier"},
    "CI_Organisation": {"contactInfo", "partyIdentifier", "individual"},
    "MD_Keywords": {"keyword"},
    "MD_LegalConstraints": {"reference", "useConstraints", "accessConstraints", "otherConstraints"},
}
"""The properties of the vector record's classes that the 19115-3 schemas let repeat (maxOccurs unbounded)."""


def read_iso(obj: ET.Element) -> dict[str, Any]:
    """A class element as docs/mapping-export.md reads ISO 19115-3: each property replaced by its value."""
    tree: dict[str, Any] = {"_class": obj.tag.rpartition("}")[2]}
    for prop in obj:
        key, children = prop.tag.rpartition("}")[2], list(prop)
        if not children:  # a gco:nilReason or an empty property
            continue
        child = children[0]
        code = child.get("codeListValue")
        value = code if code is not None else (child.text or "").strip() if not len(child) else read_iso(child)
        if key == "identificationInfo":
            tree.setdefault(key, value)  # only the first counts
        elif key in ISO_LISTS.get(tree["_class"], ()):
            tree.setdefault(key, []).append(value)
        else:
            tree[key] = value
    return tree


def test_iso_parser_vector_matches_the_reading_rules() -> None:
    case = raw_case("iso-19115-3")
    root = ET.fromstring(case["raw_input"]["text"].encode())  # noqa: S314 - the vectors ship in this package
    assert read_iso(root) == case["document"]


@pytest.mark.parametrize("tag", ["3.1", "4.0"])
def test_curated_iso_rows_read_the_vector_document(tag: str) -> None:
    paths = curated_paths(tag, "iso-19115-1-2014")
    document = raw_case("iso-19115-3")["document"]
    authors = ["Antonie van Leeuwenhoek", "Marie Skłodowska-Curie"]
    expected = {
        "author.givenName": authors,
        "author.familyName": authors,
        "author.@id": ["0000-0002-1825-0097"],
        "contributor.givenName": ["Hua Luogeng"],
        "contributor.familyName": ["Hua Luogeng"],
        "contributor.@id": [],
        "license": ["https://spdx.org/licenses/MIT.html"],
        "identifier": ["10.5555/carberry.notes", "swh:1:dir:d198bc9d7a6bcf6db04f476d29314f157507d505"],
        "keywords": ["lab notes", "reproducibility"],
        "datePublished": ["2024-05-02"],
        "publisher": ["Carberry Institute"],
        "resourceType": ["software"],
    }
    for term, values in expected.items():
        assert resolve(document, paths[term]) == values, term
    assert [p["name"] for p in resolve(document, paths["author"])] == authors
    assert [p["name"] for p in resolve(document, paths["contributor"])] == ["Hua Luogeng"]
    # name, version and description read their crosswalk cells, which have no curated row.
    mapping = json.loads((ROOT / f"examples/mapping-{tag}.json").read_text("utf-8"))
    cells = {r["term"]: r["path"] for r in mapping["rows"] if r["format"] == "iso-19115-1-2014"}
    assert resolve(document, cells["name"]) == ["carberry-notes"]
    assert resolve(document, cells["version"]) == ["1.4.0"]
    assert resolve(document, cells["description"]) == ["Keeps lab notes next to the code that produced them."]
