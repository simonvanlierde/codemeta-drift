import json
import re
import subprocess
import sys
from pathlib import Path

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
    assert data["coverage"]["codemeta_tag"] == "3.1"
    # The repo fixture's HEAD is the 4.0 snapshot: its exported cells read as at 3.1, but its files drift.
    codes = [f["code"] for f in data["upstream"]["drift"]]
    assert codes.count("CROSSWALK_ROWS") == 10
    assert "SKIPPED" not in codes
    assert data["upstream"]["cells"] == []
    assert len(data["upstream"]["commit"]) == 40
    # The crosswalks nobody reviewed are read at the export's tag, not at HEAD.
    assert data["unreviewed"]["codemeta_tag"] == "3.1"
    assert len(data["unreviewed"]["formats"]) == 36
    # The SSSOM file the page publishes is the one its own mapping_set_id names.
    tsv = (out / "spokes-3.1.sssom.tsv").read_text("utf-8")
    assert tsv.startswith("# mapping_set_id: https://simonvanlierde.com/codemeta-drift/spokes-3.1.sssom.tsv\n")
    assert sorted(p.name for p in out.iterdir()) == [
        "data.json",
        "favicon.svg",
        "fragment.mjs",
        "index.html",
        "main.mjs",
        "spokes-3.1.sssom.tsv",
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
