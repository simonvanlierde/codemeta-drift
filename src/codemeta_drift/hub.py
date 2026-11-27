"""Field correspondences joined through the curated CodeMeta export, without value conversion."""

import csv
import io
import re
from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import quote

from codemeta_drift.checks import table_rows
from codemeta_drift.export import ALL_TERMS, KINDS, NO_PROPERTY, PATH, SCHEMA_VERSION, formats, tag_key

REPO = "https://github.com/simonvanlierde/codemeta-drift/"
# w3id.org redirects this base to the coverage page, so the identifiers outlive its hosting.
BASE = "https://w3id.org/codemeta-drift/"
"""The coverage page, which resolves the hub's term, field and format identifiers to matrix cells."""


class UsageError(ValueError):
    """A bad option value, such as a format the mapping has no rows for; the command line exits 2."""


CREATOR = "orcid:0009-0006-6953-909X"
"""The curator of the mapping set, as in CITATION.cff."""

SHEET = "https://github.com/codemeta/codemeta/blob/5f192575310181535e83ea6259d156723775ad86/crosswalks-sssom/"
SHEETS = {
    "datacite": f"{SHEET}datacite/datacite-codemeta-mappings.csv",
    "zenodo": f"{SHEET}zenodo/zenodo-codemeta-mappings.csv",
    "bibtex": f"{SHEET}bibtex/bibtex-codemeta-mappings.csv",
    "swmath": f"{SHEET}swmath/swmath-codemeta-mapping.csv",
}
"""CodeMeta's own SSSOM sheets, from its sssom-methodology branch, by format."""

PREDICATES = {
    "exact_match": "skos:exactMatch",
    "close_match": "skos:closeMatch",
    # The source term is narrower, so the CodeMeta term is its broader match (skos:narrower would invert it).
    "more_specific_than": "skos:broadMatch",
    "more_generic_than": "skos:narrowMatch",
    # Its EVIDENCE path is the sheet's combined_mapping joined with " + ", so one part alone stays related.
    "part_of": "skos:closeMatch",
}
"""The SKOS mapping predicate for each relation in a sheet's type_relation column."""

EVIDENCE = {
    ("datacite", "name", "titles[].title"): "exact_match",
    ("datacite", "version", "version"): "exact_match",
    ("datacite", "author", "creators[]"): "exact_match",
    ("datacite", "author.givenName", "creators[].givenName"): "exact_match",
    ("datacite", "author.familyName", "creators[].familyName"): "exact_match",
    ("datacite", "contributor", "contributors[]"): "exact_match",
    ("datacite", "contributor.givenName", "contributors[].givenName"): "exact_match",
    ("datacite", "contributor.familyName", "contributors[].familyName"): "exact_match",
    ("datacite", "identifier", "doi"): "exact_match",
    ("datacite", "keywords", "subjects[].subject"): "exact_match",
    ("datacite", "license", "rightsList[].rightsUri"): "close_match",
    ("datacite", "publisher", "publisher.name | publisher"): "close_match",
    ("datacite", "author.name", "creators[].name"): "close_match",
    # The sheet names Zenodo REST API record keys (metadata/title); .zenodo.json holds that metadata object,
    # with the licence id the API nests in metadata/license/id.
    ("zenodo", "name", "title"): "exact_match",
    ("zenodo", "version", "version"): "exact_match",
    ("zenodo", "license", "license"): "exact_match",
    ("zenodo", "identifier", "doi"): "more_specific_than",
    ("zenodo", "description", "description"): "exact_match",
    ("zenodo", "keywords", "keywords"): "exact_match",
    ("zenodo", "datePublished", "publication_date"): "exact_match",
    ("bibtex", "author", "author"): "exact_match",
    ("bibtex", "license", "license"): "exact_match",
    ("bibtex", "identifier", "doi"): "more_specific_than",
    ("bibtex", "description", "abstract"): "exact_match",
    ("bibtex", "datePublished", "year + month"): "part_of",
    ("bibtex", "publisher", "publisher"): "exact_match",
    ("swmath", "name", "name"): "exact_match",
    ("swmath", "codeRepository", "source_code"): "exact_match",
    ("swmath", "description", "description"): "exact_match",
    ("swmath", "keywords", "keywords"): "exact_match",
}
"""The relation the format's sheet gives the field the hub reads, by format, term and the path checked against it."""


def relation(row: Mapping[str, Any]) -> str:
    """The sheet's relation for the row's current path, or "" when no sheet covers that path."""
    return EVIDENCE.get((row["format"], row["term"], row["path"]), "")


CODEMETA_PROPERTIES = {"referencePublication"}
"""The properties CodeMeta's context defines itself; every other hub property is schema.org's there."""


def codemeta_id(term: str) -> str:
    """The CodeMeta term's IRI as CodeMeta's context gives it, or the hub's own id where CodeMeta has no term.

    A person sub-term is its own property (``author.givenName`` is ``schema:givenName``), and a citation term with
    a property row is that property (``preferredCitation`` is ``codemeta:referencePublication``). A test checks
    every object against the context at each tag.
    """
    key = ALL_TERMS[term]
    if key is None or term == "swhid" or term in NO_PROPERTY or term.endswith(".@id"):
        return f"term:{quote(term, safe='')}"
    return f"{'codemeta' if key[1] in CODEMETA_PROPERTIES else 'schema'}:{key[1]}"


def validate_mapping(data: Any) -> None:  # noqa: ANN401
    """Reject malformed exports, formats predating their tag and repeated format/term pairs."""
    if not isinstance(data, dict) or not isinstance(data.get("schema_version"), str):
        msg = "mapping must have a schema_version string"
        raise ValueError(msg)  # noqa: TRY004 - malformed JSON documents share one CLI error
    if not re.fullmatch(r"1\.(0|[1-9][0-9]*)", data["schema_version"]):
        msg = f"unsupported mapping schema_version {data['schema_version']!r}"
        raise ValueError(msg)
    generator = data.get("generator")
    if (
        not isinstance(data.get("codemeta_tag"), str)
        or not data["codemeta_tag"]
        or not isinstance(generator, dict)
        or any(not isinstance(generator.get(key), str) or not generator[key] for key in ("name", "version"))
        or not isinstance(data.get("rows"), list)
    ):
        msg = "mapping needs codemeta_tag, generator name/version and rows"
        raise ValueError(msg)
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)*", data["codemeta_tag"]):
        msg = "mapping codemeta_tag must be a numeric version"
        raise ValueError(msg)
    allowed_formats = formats(data["codemeta_tag"])
    # A newer minor may add formats or relax a pattern this build does not know.
    upgrade = ""
    if int(data["schema_version"].split(".")[1]) > int(SCHEMA_VERSION.split(".")[1]):
        newer = data["schema_version"]
        upgrade = f" (schema_version {newer} is newer than this build's {SCHEMA_VERSION}; upgrade codemeta-drift)"
    seen = set()
    for i, row in enumerate(data["rows"], 1):
        if not isinstance(row, dict) or not {"format", "term", "path", "source"} <= row.keys():
            msg = f"mapping row {i} needs format, term, path and source"
            raise ValueError(msg)
        if (
            not isinstance(row["format"], str)
            or row["format"] not in allowed_formats
            or not isinstance(row["term"], str)
            or row["term"] not in ALL_TERMS
            or not isinstance(row["source"], str)
            or not re.fullmatch(r"(crosswalk:crosswalks/[^@]+\.csv@[^@\s]+|curated:\S.*)", row["source"])
            or (row["path"] is not None and (not isinstance(row["path"], str) or not PATH.fullmatch(row["path"])))
            or (row.get("crosswalk_cell") is not None and not isinstance(row["crosswalk_cell"], str))
            or any(key in row and not isinstance(row[key], str) for key in ("comment", "see_also"))
            or ("see_also" in row and not row["see_also"].startswith("https://"))
            or row.get("kind") not in (None, *KINDS)
        ):
            msg = f"invalid or unsupported mapping row {i}{upgrade}"
            raise ValueError(msg)
        key = row["format"], row["term"]
        if key in seen:
            msg = f"duplicate mapping row for {key}"
            raise ValueError(msg)
        seen.add(key)


def spokes(mapping: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate the export and add Go's module directive as a repository correspondence."""
    validate_mapping(mapping)
    return [
        *mapping["rows"],
        {
            "format": "gomod",
            "term": "codeRepository",
            "path": "module",
            "source": "curated:go.mod's module directive is a module path, not a repository URL",
        },
    ]


def pair_rows(mapping: dict[str, Any], source: str, target: str) -> list[dict[str, str]]:
    """Join non-null rows by term; the paths correspond but their values may need conversion."""
    rows = spokes(mapping)
    present = {row["format"] for row in rows}
    if source not in present or target not in present:
        msg = f"source and target must be present formats: {', '.join(sorted(present))}"
        raise UsageError(msg)
    targets = {row["term"]: row["path"] for row in rows if row["format"] == target and row["path"] is not None}
    return [
        {"term": row["term"], "source": row["path"], "target": targets[row["term"]]}
        for row in rows
        if row["format"] == source and row["path"] is not None and row["term"] in targets
    ]


def table(rows: Iterable[Mapping[str, str]], columns: list[str], delimiter: str = ",") -> str:
    """Serialize rows with proper quoting, including paths containing alternatives."""
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=columns, delimiter=delimiter, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def sssom(mapping: dict[str, Any]) -> str:
    """SSSOM 1.0 TSV spokes from format fields to CodeMeta terms, as CodeMeta's SSSOM methodology sets them out.

    A subject keeps the field's complete path, selectors and alternatives included, so it opens its coverage cell.
    Predicates are relatedMatch unless ``EVIDENCE`` holds the sheet's relation for that field.
    """
    rows = spokes(mapping)
    tag, version = mapping["codemeta_tag"], mapping["generator"]["version"]
    count = len({row["format"] for row in rows})
    # CodeMeta's context prefixes: 4.0 moved schema.org to https and its own terms to w3id.
    new = tag_key(tag) >= (4, 0)
    schema = "https://schema.org/" if new else "http://schema.org/"
    codemeta = "https://w3id.org/codemeta/terms/" if new else "https://codemeta.github.io/terms/"
    metadata = (
        f"# mapping_set_id: {BASE}spokes-{tag}.sssom.tsv\n"
        f"# mapping_set_version: '{version}'\n"
        f"# mapping_set_title: codemeta-drift crosswalk hub spokes for CodeMeta {tag}\n"
        f"# mapping_set_description: Field correspondences from {count} metadata formats to CodeMeta's terms"
        " (codemeta-drift's hub terms where CodeMeta has none),"
        " from the reviewed mapping export, which starts from CodeMeta's crosswalks"
        " (Apache-2.0, the CodeMeta contributors). The paths correspond; their values may need conversion.\n"
        f"# mapping_provider: {REPO}\n"
        "# creator_id:\n"
        f"#   - {CREATOR}\n"
        "# see_also:\n"
        f"#   - {REPO}blob/main/docs/crosswalk-hub.md\n"
        "# license: https://spdx.org/licenses/Apache-2.0.html\n"
        "# sssom_version: '1.0'\n"
        "# curie_map:\n"
        f"#   term: {BASE}#term/\n"
        f"#   field: {BASE}#field/\n"
        f"#   format: {BASE}#format/\n"
        "#   orcid: https://orcid.org/\n"
        "#   skos: http://www.w3.org/2004/02/skos/core#\n"
        "#   semapv: https://w3id.org/semapv/vocab/\n"
        f"#   schema: {schema}\n"
        f"#   codemeta: {codemeta}\n"
    )
    mappings = [
        {
            "subject_id": f"field:{row['format']}/{quote(row['path'], safe='')}",
            "subject_label": row["path"],
            "predicate_id": PREDICATES[relation(row)] if relation(row) else "skos:relatedMatch",
            "object_id": codemeta_id(row["term"]),
            "object_label": row["term"],
            "mapping_justification": "semapv:ManualMappingCuration",
            "subject_source": f"format:{row['format']}",
            # Only a CodeMeta term comes from CodeMeta's context; a hub term has no source to version.
            "object_source": "" if codemeta_id(row["term"]).startswith("term:") else f"https://w3id.org/codemeta/{tag}",
            "object_source_version": "" if codemeta_id(row["term"]).startswith("term:") else tag,
            "see_also": SHEETS[row["format"]] if relation(row) else "",
            "comment": row["source"] + (f"; {row['comment']}" if row.get("comment") else ""),
        }
        for row in rows
        if row["path"] is not None
    ]
    return metadata + table(
        mappings,
        [
            "subject_id",
            "subject_label",
            "predicate_id",
            "object_id",
            "object_label",
            "mapping_justification",
            "subject_source",
            "object_source",
            "object_source_version",
            "see_also",
            "comment",
        ],
        "\t",
    )


def crosswalk(mapping: dict[str, Any], files: Mapping[str, str], fmt: str) -> str:
    """CodeMeta's two-column layout, with the property table's order and duplicate rows.

    Person rows describe the author mapping, since the property table has no separate contributor
    person rows. The synthetic swhid term must not replace the software identifier (DOI).
    """
    rows = spokes(mapping)
    if fmt not in {row["format"] for row in rows}:
        msg = f"unknown format {fmt!r}"
        raise UsageError(msg)
    paths = {
        ALL_TERMS[row["term"]]: row["path"] or ""
        for row in rows
        if row["format"] == fmt
        and ALL_TERMS.get(row["term"])
        and row["term"] != "swhid"
        and not row["term"].startswith("contributor.")
    }
    return table(
        [{"Property": row[1], fmt: paths.get((row[0], row[1]), "")} for _, row in table_rows(files)], ["Property", fmt]
    )
