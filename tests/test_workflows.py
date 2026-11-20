import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("case", "pushed"),
    [
        ("api-failure", False),
        ("remote-failure", False),
        ("human", False),
        ("advanced", False),
        ("bot", True),
        ("missing", True),
    ],
)
def test_copier_update_preserves_unverified_or_changed_remote_commits(tmp_path: Path, case: str, *, pushed: bool):
    workflow = (ROOT / ".github/workflows/copier-update.yml").read_text("utf-8")
    section = workflow.split("          # Someone resolving", 1)[1].split("          # With a .rej", 1)[0]
    script = "\n".join(line[10:] for line in ("          # Someone resolving" + section).splitlines())
    fake = r"""
    gh() {
      if [ "$1" = api ]; then
        if [ "$CASE" = api-failure ]; then return 1; fi
        if [ "$CASE" = human ]; then echo maintainer@example.org;
        else echo '41898282+github-actions[bot]@users.noreply.github.com'; fi
      fi
    }
    git() {
      if [ "$1" = ls-remote ]; then
        if [ "$CASE" = remote-failure ]; then return 1; fi
        if [ "$CASE" != missing ]; then printf '%s\t%s\n' abc123 refs/heads/chore/copier-update; fi
      else
        if [ "$CASE" = missing ]; then expected=''; else expected=abc123; fi
        case " $* " in
          *" --force-with-lease=refs/heads/chore/copier-update:$expected "*)
            if [ "$CASE" = advanced ]; then return 1; fi ;;
        esac
        touch "$PUSHED"
      fi
    }
    branch=chore/copier-update
    """
    marker = tmp_path / "pushed"
    result = subprocess.run(
        ["bash", "-euo", "pipefail", "-c", fake + script],
        env={
            "PATH": os.defpath,
            "CASE": case,
            "REPO": "example/tool",
            "BASE": "main",
            "PUSHED": str(marker),
            "GITHUB_STEP_SUMMARY": str(tmp_path / "summary"),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert marker.exists() is pushed, result.stdout + result.stderr
    if pushed:
        assert result.returncode == 0, result.stderr
