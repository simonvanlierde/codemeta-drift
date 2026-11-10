import contextlib
import importlib.util
import json
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

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
    # Read at 3.1, not the newest tag: these two crosswalks exist only in the 4.0 fixture.
    assert {f["format"] for f in older["unreviewed"]["formats"]}.isdisjoint({"GitLab", "code-json"})
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


def test_build_without_a_clone_has_no_upstream_or_unreviewed(tmp_path: Path):
    out = tmp_path / "site"
    assert build(out).returncode == 0
    data = json.loads((out / "data.json").read_text("utf-8"))
    older = json.loads((out / "data-3.1.json").read_text("utf-8"))
    assert data["upstream"] is data["unreviewed"] is older["unreviewed"] is None


def test_a_clone_without_an_older_tag_fails_cleanly(tmp_path: Path, repo: Path, git: Callable[..., None]):
    out = tmp_path / "site"
    assert build(out, "--codemeta", str(repo)).returncode == 0
    before = sorted(p.name for p in out.iterdir())
    git(repo, "tag", "-d", "3.1")
    result = build(out, "--codemeta", str(repo))
    assert result.returncode == 2
    assert "3.1" in result.stderr
    assert "Traceback" not in result.stderr
    assert sorted(p.name for p in out.iterdir()) == before


def test_a_malformed_upstream_file_fails_cleanly(tmp_path: Path, repo: Path, git: Callable[..., None]):
    (repo / "properties_description.csv").write_bytes(b"Parent Type,Property\nschema:Thing,n\xefme\n")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "broken")
    result = build(tmp_path / "site", "--codemeta", str(repo))
    assert result.returncode == 2
    assert "Traceback" not in result.stderr


def test_out_that_is_a_file_is_a_usage_error(tmp_path: Path):
    (tmp_path / "afile").write_text("keep me")
    result = build(tmp_path / "afile")
    assert result.returncode == 2
    assert (tmp_path / "afile").read_text() == "keep me"


def test_a_failure_after_the_data_leaves_out_replaceable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Whatever fails mid-build, the next build can replace what it left: data.json goes in first."""
    spec = importlib.util.spec_from_file_location("site_build", ROOT / "site/build.py")
    assert spec
    assert spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    out = tmp_path / "site"

    def full(*_: object, **__: object) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(sys, "argv", ["build.py", "--out", str(out)])
    monkeypatch.setattr(module, "sssom", full)
    with contextlib.suppress(OSError, SystemExit):
        module.main()
    monkeypatch.undo()
    assert build(out).returncode == 0


def test_every_id_main_mjs_looks_up_is_in_the_page():
    source = (ROOT / "site/main.mjs").read_text("utf-8")
    html = (ROOT / "site/index.html").read_text("utf-8")
    ids = set(re.findall(r'getElementById\("([\w-]+)"\)', source))
    assert ids
    assert {i for i in ids if f'id="{i}"' not in html} == set()


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
