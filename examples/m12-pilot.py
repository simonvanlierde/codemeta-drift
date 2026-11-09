"""Rehearse candidate ranking and human review offline; scores are uncalibrated."""

# ruff: noqa: INP001 - standalone example, not an importable package

import argparse
import csv
import hashlib
import json
import math
import platform
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

from codemeta_drift.export import TERMS

ROOT = Path(__file__).resolve().parents[1]
MAPPING = ROOT / "examples/mapping-4.0.json"
PROPERTIES = ROOT / "tests/fixtures/4.0/properties_description.csv"
SELECTION = (
    ("cff-1.2.0", "name"),
    ("cff-1.2.0", "author.familyName"),
    ("pep621", "version"),
    ("cargo", "codeRepository"),
    ("zenodo", "description"),
    ("npm", "keywords"),
    ("datacite", "publisher"),
    ("ris", "datePublished"),
    ("gitlab", "license"),
    ("code-json-2.0", "name"),
)
METHODS = {
    "jaccard": "Token-set Jaccard over target labels",
    "characters": "SequenceMatcher ratio over normalized target labels",
    "tfidf": "Cosine of raw token counts times log((N+1)/(df+1))+1; labels plus descriptions",
}


def tokens(text: str) -> list[str]:
    """Split camel case and punctuation without expanding abbreviations or synonyms."""
    return re.findall(r"[a-z0-9]+", re.sub(r"([a-z])([A-Z])", r"\1 \2", text).lower())


def load_targets() -> dict[str, tuple[str, str]]:
    """Use exactly the hub terms and their matching property-table descriptions."""
    with PROPERTIES.open(encoding="utf-8", newline="") as stream:
        descriptions = {(r["Parent Type"], r["Property"]): r["Description"] for r in csv.DictReader(stream)}
    return {term: (" ".join(tokens(term)), descriptions.get(key, "")) for term, key in TERMS.items()}


def rank(path: str, targets: dict[str, tuple[str, str]], method: str) -> list[tuple[str, float]]:
    """Rank only source paths; omit zero-support candidates and break ties alphabetically."""
    query = tokens(path)
    documents = {term: tokens(f"{label} {description}") for term, (label, description) in targets.items()}
    vocabulary = set().union(*(set(doc) for doc in documents.values()))
    idf = {
        word: math.log((len(documents) + 1) / (1 + sum(word in d for d in documents.values()))) + 1
        for word in vocabulary
    }
    query_vector = {word: count * idf[word] for word, count in Counter(query).items() if word in idf}
    scores = []
    for term, (label, _) in targets.items():
        if method == "jaccard":
            left, right = set(query), set(tokens(label))
            score = len(left & right) / len(left | right) if left | right else 0.0
        elif method == "characters":
            score = SequenceMatcher(None, " ".join(query), label).ratio() if query else 0.0
        elif method == "tfidf":
            vector = {word: count * idf[word] for word, count in Counter(documents[term]).items()}
            norm = math.sqrt(sum(v * v for v in query_vector.values()) * sum(v * v for v in vector.values()))
            score = sum(value * vector.get(word, 0.0) for word, value in query_vector.items()) / norm if norm else 0.0
        else:
            raise ValueError(method)
        if score > 0:
            scores.append((term, score))
    return sorted(scores, key=lambda row: (-row[1], row[0]))[:3]


def write_tsv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    """Write stable tab-separated files with explicit columns."""
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run(out: Path) -> None:
    """Create a fresh review bundle, keeping references separate from human decisions."""
    mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
    targets = load_targets()
    cases = []
    reference = []
    for index, (fmt, term) in enumerate(SELECTION, 1):
        row = next(r for r in mapping["rows"] if r["format"] == fmt and r["term"] == term)
        if not isinstance(row["path"], str) or not row["path"]:
            message = f"missing selected source path: {fmt}/{term}"
            raise ValueError(message)
        cases.append({"case_id": str(index), "format": fmt, "source_path": row["path"]})
        reference.append({"case_id": str(index), "expected_term": term, "reference_kind": "curated mapping"})
    for index, path, kind in ((11, "qxz", "no-match control"), (12, "funding", "outside target subset")):
        cases.append({"case_id": str(index), "format": "control", "source_path": path})
        reference.append({"case_id": str(index), "expected_term": "", "reference_kind": kind})
    candidates = []
    reviews = []
    for case in cases:
        review = {**case, "accepted_term": "", "decision": "", "reviewer": ""}
        for method in METHODS:
            ranked = rank(case["source_path"], targets, method)
            review[f"{method}_candidates"] = " | ".join(term for term, _ in ranked)
            for position, (term, score) in enumerate(ranked or [("", 0.0)], 1):
                candidates.append(
                    {
                        **case,
                        "method": method,
                        "rank": str(position) if term else "",
                        "candidate_term": term,
                        "score": f"{score:.8f}",
                    }
                )
        reviews.append(review)
    inputs = (MAPPING, PROPERTIES, Path(__file__), ROOT / "src/codemeta_drift/export.py")
    manifest = {
        "python": platform.python_version(),
        "codemeta_tag": mapping["codemeta_tag"],
        "generator": mapping["generator"],
        "methods": METHODS,
        "candidate_terms": sorted(targets),
        "inputs_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        "limits": "Handpicked lexical rehearsal; uncalibrated scores and curated references, not study accuracy.",
    }
    out.mkdir(parents=True, exist_ok=False)
    write_tsv(out / "candidates.tsv", [*cases[0], "method", "rank", "candidate_term", "score"], candidates)
    write_tsv(out / "review.tsv", [key for key in reviews[0] if key != "source_path"] + ["source_path"], reviews)
    write_tsv(out / "reference.tsv", ["case_id", "expected_term", "reference_kind"], reference)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="new directory for candidates and blank human review")
    run(parser.parse_args().out)
