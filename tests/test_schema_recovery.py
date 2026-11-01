"""The offline recovery example keeps the original pin until an explicit review is supplied."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("approved", [False, True])
def test_offline_schema_recovery(tmp_path: Path, *, approved: bool):
    mapping = ROOT / "examples/mapping-3.1.json"
    original = mapping.read_bytes()
    out = tmp_path / "result"
    args = [sys.executable, str(ROOT / "examples/schema-recovery.py"), str(out)]
    if approved:
        args += ["--approval", str(ROOT / "examples/schema-recovery-approval.json")]
    subprocess.run(args, check=True, capture_output=True, text=True, cwd=tmp_path)
    report = json.loads((out / "report.json").read_text())
    assert report == {
        "broken": ["PATH_NOT_IN_SCHEMA pep621: name: project.name: no 'name'"],
        "repeated_drafts": [],
        "approved": approved,
    }
    assert len(json.loads((out / "drafts.json").read_text())) == 1
    result = (out / "mapping.json").read_bytes()
    pin = json.loads((out / "pin.json").read_text())
    assert pin["mapping_sha256"] == hashlib.sha256(result).hexdigest()
    assert (
        pin["schema_sha256"]
        == hashlib.sha256((ROOT / "src/codemeta_drift/mapping.schema.json").read_bytes()).hexdigest()
    )
    assert (result != original) is approved
    Draft202012Validator(json.loads((ROOT / "src/codemeta_drift/mapping.schema.json").read_text())).validate(
        json.loads(result)
    )
    assert mapping.read_bytes() == original


def test_recovery_rejects_an_unrelated_approval(tmp_path: Path):
    approval = tmp_path / "approval.json"
    approval.write_text('{"format":"npm","reason":"different change"}')
    out = tmp_path / "result"
    result = subprocess.run(
        [sys.executable, str(ROOT / "examples/schema-recovery.py"), str(out), "--approval", str(approval)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "approval does not describe" in result.stderr
    assert not out.exists()


@pytest.mark.parametrize("invalid", ["malformed-approval", "missing-approval", "existing-output"])
def test_recovery_input_errors_leave_existing_files_alone(invalid: str, tmp_path: Path):
    approval = tmp_path / "approval.json"
    out = tmp_path / "result"
    args = [sys.executable, str(ROOT / "examples/schema-recovery.py"), str(out)]
    if invalid == "existing-output":
        out.mkdir()
        (out / "keep.txt").write_text("existing output")
    else:
        if invalid == "malformed-approval":
            approval.write_text("{broken")
        args += ["--approval", str(approval)]
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    assert result.returncode == 2
    assert "error:" in result.stderr
    assert "Traceback" not in result.stderr
    if invalid == "existing-output":
        assert list(out.iterdir()) == [out / "keep.txt"]
        assert (out / "keep.txt").read_text() == "existing output"
    else:
        assert not out.exists()
