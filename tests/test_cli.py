import json
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from codemeta_drift.cli import is_input, main

FIXTURES = Path(__file__).parent / "fixtures"


def test_ref_reads_the_commit_not_the_working_tree(repo: Path, capsys: pytest.CaptureFixture[str]):
    assert main([str(repo), "--ref", "3.1"]) == 1
    assert capsys.readouterr().out.splitlines() == (FIXTURES / "3.1.expected").read_text("utf-8").splitlines()


def test_working_tree_and_json_output(repo: Path, capsys: pytest.CaptureFixture[str]):
    assert main([str(repo), "--json"]) == 1
    findings = json.loads(capsys.readouterr().out)
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


def test_star_does_not_cross_directories():
    assert is_input("crosswalks/Zenodo.csv")
    assert is_input("codemeta.json")
    assert not is_input("crosswalks/old/Zenodo.csv")
    assert not is_input("scripts/data.csv")
