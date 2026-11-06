import json
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from codemeta_drift.checks import Finding
from codemeta_drift.cli import is_input, main
from codemeta_drift.conformance import SCHEMA_FILES

FIXTURES = Path(__file__).parent / "fixtures"


def test_ref_reads_the_commit_not_the_working_tree(repo: Path, capsys: pytest.CaptureFixture[str]):
    assert main([str(repo), "--ref", "3.1"]) == 1
    assert capsys.readouterr().out.splitlines() == (FIXTURES / "3.1.expected").read_text("utf-8").splitlines()


def test_working_tree_and_json_output(repo: Path, capsys: pytest.CaptureFixture[str]):
    assert main([str(repo), "--json"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert set(report) == {"version", "tool", "findings"}
    assert report["version"] == 1
    assert report["tool"]["name"] == "codemeta-drift"
    findings = report["findings"]
    assert all(set(f) == {"code", "file", "term", "detail"} for f in findings)
    assert any(f["code"] == "AGGREGATE_FORMAT" and f["term"] == "GitLab" for f in findings)


def test_ref_and_working_tree_read_the_same_files(
    repo: Path, git: Callable[..., None], capsys: pytest.CaptureFixture[str]
):
    """Includes a non-ASCII name, which git quotes unless asked not to, and a file no check reads."""
    shutil.copy(repo / "crosswalks/GitLab.csv", repo / "crosswalks/Gitläb.csv")
    (repo / "examples/notes.txt").write_text("not an input")
    git(repo, "add", "-A")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "extra")
    main([str(repo)])
    tree = capsys.readouterr().out
    main([str(repo), "--ref", "HEAD"])
    assert capsys.readouterr().out == tree
    assert "crosswalks/Gitläb.csv" in tree


def test_a_directory_named_like_an_input_is_skipped(repo: Path, capsys: pytest.CaptureFixture[str]):
    """As --ref skips it, since git lists only files."""
    (repo / "examples/dir.json").mkdir()
    code = main([str(repo)])
    tree = capsys.readouterr().out
    assert (main([str(repo), "--ref", "HEAD"]), capsys.readouterr().out) == (code, tree)
    assert code != 2


@pytest.mark.parametrize("args", [["--ref", "no-such-ref"], ["--ref=--output=x"]])
def test_bad_ref_exits_2(repo: Path, args: list[str], capsys: pytest.CaptureFixture[str]):
    assert main([str(repo), *args]) == 2
    err = capsys.readouterr().err
    assert "fatal:" in err
    assert "b'" not in err  # git's message, decoded


def test_directory_without_codemeta_files_exits_2(tmp_path: Path):
    assert main([str(tmp_path)]) == 2


def test_project_with_only_a_codemeta_json_exits_2(tmp_path: Path):
    """A software project's own metadata is not a codemeta checkout: nothing would be compared."""
    (tmp_path / "codemeta.json").write_text('{"name": "x"}')
    assert main([str(tmp_path)]) == 2


@pytest.mark.parametrize(
    ("path", "content"),
    [
        ("codemeta.jsonld", b"{bad"),
        ("codemeta.jsonld", b'{"@context": [{"name": "schema:name"}]}'),
        ("properties_description.csv", b"Parent Type,Property\nschema:Thing,n\xefme\n"),
        ("crosswalk.csv", b""),
    ],
)
def test_malformed_file_exits_2_not_1(repo: Path, path: str, content: bytes):
    (repo / path).write_bytes(content)
    assert main([str(repo)]) == 2


def test_no_drift_exits_0(tmp_path: Path):
    (tmp_path / "codemeta.jsonld").write_text('{"@context": {"name": "schema:name"}}')
    (tmp_path / "properties_description.csv").write_text("Parent Type,Property\nschema:Thing,name\n")
    assert main([str(tmp_path)]) == 0


def test_no_findings_prints_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    (tmp_path / "codemeta.jsonld").write_text("{}")
    (tmp_path / "properties_description.csv").write_text("")
    monkeypatch.setattr("codemeta_drift.cli.check", lambda _: [])
    assert main([str(tmp_path)]) == 0
    assert capsys.readouterr().out == ""


def test_star_does_not_cross_directories():
    assert is_input("crosswalks/Zenodo.csv")
    assert is_input("codemeta.json")
    assert not is_input("crosswalks/old/Zenodo.csv")
    assert not is_input("scripts/data.csv")


def test_version(capsys: pytest.CaptureFixture[str]):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.startswith("codemeta-drift 0.")


def _watch_args(tmp_path: Path, repo: Path, *, tag: str = "3.1", source: str = "tag v0.3.0\n") -> list[str]:
    (tmp_path / "MAPPING_SOURCE").write_text(source)
    (tmp_path / "existing.json").write_text("[]")
    (tmp_path / "schemas").mkdir(exist_ok=True)
    for name in SCHEMA_FILES.values():
        (tmp_path / "schemas" / name).write_text("{}")
    schemas = str(tmp_path / "schemas")
    return [
        *("watch", str(repo), "--tag", tag, "--before", schemas, "--after", schemas),
        *("--citesync-source", str(tmp_path / "MAPPING_SOURCE"), "--latest", "v0.4.0"),
        *("--existing", str(tmp_path / "existing.json")),
    ]


def test_watch_exits_1_and_lists_the_findings_when_the_export_is_blocked(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    finding = Finding("CURATED_DUPLICATE", "GitLab", "name", "second row for gitlab")
    monkeypatch.setattr("codemeta_drift.cli.export", lambda *_: ({"rows": []}, [finding]))
    assert main(_watch_args(tmp_path, repo)) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.strip() == str(finding)


def test_watch_with_an_unknown_tag_exits_2_with_gits_message(
    repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    assert main(_watch_args(tmp_path, repo, tag="no-such-tag")) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("codemeta-drift: fatal:")


def test_watch_with_two_pin_tags_exits_2(repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    assert main(_watch_args(tmp_path, repo, source="tag v0.3.0\ntag v0.4.0\n")) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "exactly one tag line" in captured.err
