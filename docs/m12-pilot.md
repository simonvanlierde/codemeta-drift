# Offline candidate-ranking rehearsal

This small run exercises candidate ranking and a human review sheet for crosswalk mappings.
It uses three lexical baselines and the 19 terms in the hub, including its compound person terms.
It does not test a full CodeMeta vocabulary, embeddings or language models.

## Material Passport

- Type: code experiment rehearsal, run on 2026-11-07.
- Inputs: ten handpicked, non-null paths from the CodeMeta 4.0 mapping export and two controls.
- Output: [saved run](../examples/m12-pilot-run/manifest.json), with input hashes and Python version.
- Verification: repeated runs in the same environment produce identical files.
- Human review: pending for all twelve cases; the existing curated mappings are comparison references.

## Run it

From a source checkout with the development environment installed:

```sh
uv run --offline --no-sync python examples/m12-pilot.py --out /tmp/m12-pilot
```

Use a new output directory each time. An existing directory is refused so a rerun cannot overwrite
review decisions. The script reads only local files and needs no model downloads or service credentials.

The source paths come from CFF, PEP 621, Cargo, Zenodo, npm, DataCite, RIS, GitLab and code.json.
Selection uses the curated term to pick each case; the rankers receive only its source path and the
target labels and descriptions. They do not receive the curated answer, row comments or crosswalk cells.
One control is `qxz`, with no character or token support; the other is `funding`, outside the 19-term subset.

| Ranker | Comparison |
| --- | --- |
| Jaccard | Token overlap between a source path and a target label |
| Characters | SequenceMatcher ratio between normalized paths and labels |
| TF-IDF | Cosine similarity using target labels and property-table descriptions |

Camel case and punctuation separate tokens. The script adds no synonyms, stems or abbreviations.
Each ranker returns up to three positive scores, with alphabetical term order for ties.
An empty result means no lexical support. A positive score is not a confidence estimate or an acceptance.

## Inspect the saved run

Open [review.tsv](../examples/m12-pilot-run/review.tsv), which has one row per case and each ranker's
candidate list. Fill `decision` with `accept`, `reject` or `abstain`, put the chosen term in
`accepted_term` for an acceptance, and fill `reviewer`. A reviewer can choose a term outside the proposed
lists. Every saved decision is blank.

[candidates.tsv](../examples/m12-pilot-run/candidates.tsv) holds the individual ranks and scores.
[reference.tsv](../examples/m12-pilot-run/reference.tsv) keeps the existing curated terms separate;
compare it only after reviewing. The controls have no expected term in this candidate subset.

The run exposes limits that a later comparison must handle: `title` and RIS `PY` have no token overlap
with their curated targets, and character similarity still proposes unrelated terms for `funding`.
Exact labels can also compete with person sub-terms when their descriptions share words.
No score threshold was tuned to these cases.

These handpicked cases rehearse the workflow; they cannot estimate performance on unseen mappings.
The full M12 comparison with ontology tools, retrieval and local language models remains separate.
These outputs are not evidence for the entity-linking study.
