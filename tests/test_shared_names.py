import hashlib
import json
import unicodedata
from pathlib import Path

import pytest

from codemeta_drift.cli import read_dir
from codemeta_drift.export import export

FIXTURE = Path(__file__).parent / "fixtures/shared-names"
CORPUS = json.loads((FIXTURE / "people-v1.json").read_text(encoding="utf-8"))


def test_canonical_corpus_pin():
    data = (FIXTURE / "people-v1.json").read_bytes()
    source = json.loads((FIXTURE / "SOURCE.json").read_text(encoding="utf-8"))
    assert CORPUS["version"] == 1
    assert source["source_revision_kind"] == "git-blob"
    assert source["source_path"] == "conformance/names/people-v1.json"
    assert source["license"] == "MIT"
    assert (FIXTURE / source["license_file"]).is_file()
    assert hashlib.sha256(data).hexdigest() == source["sha256"]
    assert hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == source["source_revision"]  # noqa: S324 - Git's content identifier, not a security digest.


@pytest.fixture(scope="module")
def cff_mapping():
    mapping, findings = export(read_dir(Path(__file__).parent / "fixtures/3.1"), "3.1")
    assert not findings
    return {row["term"]: row for row in mapping["rows"] if row["format"] == "cff-1.2.0"}


@pytest.mark.parametrize("case", CORPUS["cases"], ids=lambda case: case["id"])
def test_documented_cff_fold_against_shared_cases(case: dict, cff_mapping: dict):
    assert cff_mapping["author.givenName"]["path"] == "authors[].given-names"
    assert cff_mapping["author.familyName"]["path"] == "authors[].family-names"
    fields = ("name-particle", "family-names", "name-suffix")
    comment = cff_mapping["author.familyName"]["comment"]
    assert [comment.index(field) for field in fields] == sorted(comment.index(field) for field in fields)
    # This executable contract checks the documented adapter rule; the hub does not convert people.
    folded = " ".join(case["cff"][field] for field in fields if case["cff"].get(field))
    assert unicodedata.normalize("NFC", folded) == case["codemeta"]["familyName"]
    assert unicodedata.normalize("NFC", case["cff"]["given-names"]) == case["codemeta"]["givenName"]
