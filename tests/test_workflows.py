import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("case", "pushed"),
    [
        ("api-failure", False),
        ("later-page-failure", False),
        ("later-page-human", False),
        ("unknown-author", False),
        ("remote-failure", False),
        ("human", False),
        ("advanced", False),
        ("bot", True),
        ("missing", True),
    ],
)
def test_copier_update_preserves_unverified_or_changed_remote_commits(tmp_path: Path, case: str, *, pushed: bool):
    workflow = (ROOT / ".github/workflows/copier-update.yml").read_text("utf-8")
    section = workflow.split("          # Git uses the credential", 1)[1].split("          # With a .rej", 1)[0]
    script = "\n".join(line[10:] for line in ("          # Git uses the credential" + section).splitlines())
    fake = r"""
    gh() {
      if [ "$1" = api ]; then
        if [ "$CASE" = api-failure ]; then return 1; fi
        if [ "$CASE" = human ]; then echo maintainer@example.org; return; fi
        echo '41898282+github-actions[bot]@users.noreply.github.com'
        if [[ " $* " == *" --paginate repos/example/tool/compare/main...abc123?per_page=100 "* ]]; then
          case "$CASE" in
            later-page-failure) return 1 ;;
            later-page-human) echo maintainer@example.org ;;
          esac
        fi
        if [[ "$CASE" = unknown-author && "$*" == *'then "unknown"'* ]]; then echo unknown; fi
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
          *) return 98 ;;
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


def test_copier_update_keeps_older_pull_request_when_workflows_need_app(tmp_path: Path):
    workflow = (ROOT / ".github/workflows/copier-update.yml").read_text("utf-8")
    start = '          if [ "$HAS_TOKEN" != true ] && [ "$WORKFLOWS" = true ]; then'
    section = workflow.split(start, 1)[1].split('          if [ "$HAS_TOKEN" != true ]; then', 1)[0]
    script = "\n".join(line[10:] for line in (start + section).splitlines())
    fake = r"""
    gh() {
      case "$1 $2" in
        "issue list") echo 12 ;;
        "pr list") echo 34 ;;
        *) echo "unexpected gh command: $1 $2" >&2; return 98 ;;
      esac
    }
    branch=chore/copier-update
    own='map(select(.isCrossRepository == false))'
    """
    result = subprocess.run(
        ["bash", "-euo", "pipefail", "-c", fake + script],
        cwd=tmp_path,
        env={"PATH": os.defpath, "HAS_TOKEN": "false", "WORKFLOWS": "true", "LATEST": "v1.2.3"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Pull request #34 is still open" in result.stdout
