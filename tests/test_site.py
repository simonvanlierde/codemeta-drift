import json
import re
import subprocess
import sys
from pathlib import Path

from codemeta_drift.export import FORMATS

ROOT = Path(__file__).resolve().parents[1]


def build(out: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "site/build.py"), "--out", str(out), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_build_writes_the_page_and_upstream_data(tmp_path: Path, repo: Path):
    out = tmp_path / "site"
    assert build(out, "--codemeta", str(repo)).returncode == 0
    data = json.loads((out / "data.json").read_text("utf-8"))
    assert data["coverage"]["codemeta_tag"] == "4.0"
    assert data["tags"] == ["3.1", "4.0"]
    # The repo fixture's HEAD is the 4.0 snapshot, the exported tag: its cells read the same.
    codes = [f["code"] for f in data["upstream"]["drift"]]
    assert codes.count("CROSSWALK_ROWS") == 10
    assert "SKIPPED" not in codes
    assert data["upstream"]["cells"] == []
    assert len(data["upstream"]["commit"]) == 40
    # The crosswalks nobody reviewed are read at the export's tag.
    assert data["unreviewed"]["codemeta_tag"] == "4.0"
    assert {fmt["format"] for fmt in data["unreviewed"]["formats"]} == {
        "ASCL",
        "codemeta-V1",
        "csdms",
        "DCAT",
        "Debian Package",
        "Dublin Core",
        "ISO_19115-1",
        "MODS",
        "OntoSoft",
        "SciCrunchRegistry",
        "Software Discovery Index",
        "Software Ontology",
        "spase-v2.6.1",
        "Trove Software Map",
        "usgs-modelcatalog",
        "VIVO",
    }
    # The SSSOM file the page publishes is the one its own mapping_set_id names.
    tsv = (out / "spokes-4.0.sssom.tsv").read_text("utf-8")
    assert tsv.startswith("# mapping_set_id: https://w3id.org/codemeta-drift/spokes-4.0.sssom.tsv\n")
    old = (out / "spokes-3.1.sssom.tsv").read_text("utf-8")
    assert old.startswith("# mapping_set_id: https://w3id.org/codemeta-drift/spokes-3.1.sssom.tsv\n")
    # An older release has its own matrix, read at its own tag, and no upstream check.
    older = json.loads((out / "data-3.1.json").read_text("utf-8"))
    assert sorted(older) == ["coverage", "unreviewed"]
    assert older["coverage"]["codemeta_tag"] == older["unreviewed"]["codemeta_tag"] == "3.1"
    assert sorted(p.name for p in out.iterdir()) == [
        "data-3.1.json",
        "data.json",
        "favicon.svg",
        "fragment.mjs",
        "index.html",
        "main.mjs",
        "spokes-3.1.sssom.tsv",
        "spokes-4.0.sssom.tsv",
        "style.css",
    ]


def test_page_keeps_its_csp_and_no_inline_code():
    html = (ROOT / "site/index.html").read_text("utf-8")
    assert "default-src 'none'" in html
    assert not re.search(r"<script(?![^>]*\bsrc=)", html)
    assert "<style" not in html
    assert " style=" not in html


def test_build_refuses_a_directory_it_did_not_make(tmp_path: Path):
    (tmp_path / "notes.txt").write_text("keep me")
    result = build(tmp_path)
    assert result.returncode == 2
    assert (tmp_path / "notes.txt").read_text() == "keep me"


def test_every_format_has_a_label():
    """The page shows a raw format id, sorted last, for a format LABELS lacks."""
    source = (ROOT / "site/main.mjs").read_text("utf-8")
    block = re.search(r"const LABELS = \{(.*?)\};", source, re.DOTALL)
    assert block
    labels = set(re.findall(r'"?([a-z0-9.-]+)"?: "', block[1]))
    assert labels == set(FORMATS) - {"codemeta"}  # codemeta is the hub, not a spoke
