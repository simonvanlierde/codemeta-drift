import csv
import inspect
import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def pilot():
    return runpy.run_path(str(ROOT / "examples/m12-pilot.py"))


@pytest.mark.parametrize("method", ["jaccard", "characters", "tfidf"])
def test_rankers_are_gold_blind_and_abstain_without_support(method: str):
    module = pilot()
    targets = module["load_targets"]()
    assert len(targets) == 19
    assert list(inspect.signature(module["rank"]).parameters) == ["path", "targets", "method"]
    assert module["rank"]("codeRepository", targets, method)[0][0] == "codeRepository"
    assert module["rank"]("qxz", targets, method) == []
    tied = {"z": ("name", ""), "a": ("name", "")}
    assert [term for term, _ in module["rank"]("name", tied, method)] == ["a", "z"]


def test_run_is_deterministic_keeps_reviews_empty_and_refuses_overwrite(tmp_path: Path):
    module = pilot()
    first, second = tmp_path / "first", tmp_path / "second"
    module["run"](first)
    module["run"](second)
    assert {p.name: p.read_bytes() for p in first.iterdir()} == {p.name: p.read_bytes() for p in second.iterdir()}
    with (first / "review.tsv").open(encoding="utf-8") as stream:
        reviews = list(csv.DictReader(stream, delimiter="\t"))
    assert len(reviews) == 12
    assert all(not row[key] for row in reviews for key in ("accepted_term", "decision", "reviewer"))
    assert all(f"{method}_candidates" in row for row in reviews for method in module["METHODS"])
    with (first / "reference.tsv").open(encoding="utf-8") as stream:
        reference = list(csv.DictReader(stream, delimiter="\t"))
    assert len(reference) == 12
    assert sum(bool(row["expected_term"]) for row in reference) == 10
    with (first / "candidates.tsv").open(encoding="utf-8") as stream:
        candidates = list(csv.DictReader(stream, delimiter="\t"))
    assert {row["method"] for row in candidates} == {"jaccard", "characters", "tfidf"}
    assert all("expected_term" not in row and "accepted_term" not in row for row in candidates)
    assert not any(row["candidate_term"] for row in candidates if row["case_id"] == "11")
    with pytest.raises(FileExistsError):
        module["run"](first)
