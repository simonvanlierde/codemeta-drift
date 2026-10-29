import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

# The user's and the system's git config can add hooks or identity rules that reject the test commits.
HERMETIC_GIT = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, env=HERMETIC_GIT)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A git repository whose first commit is the 3.1 fixture and second the 4.0 fixture."""
    git(tmp_path, "init", "-q")
    for tag in ("3.1", "4.0"):
        shutil.copytree(FIXTURES / tag, tmp_path, dirs_exist_ok=True)
        git(tmp_path, "add", "-A")
        git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", tag)
        git(tmp_path, "tag", tag)
    return tmp_path


@pytest.fixture
def tagged(tmp_path: Path) -> Callable[[dict[str, str]], Path]:
    """Makes a git repository whose tag 3.1 holds the given files (path -> text)."""

    def make(files: dict[str, str]) -> Path:
        root = tmp_path / "tagged"
        git(root.parent, "init", "-q", root.name)
        for path, text in files.items():
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_text(text, encoding="utf-8")
        git(root, "add", "-A")
        git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "3.1")
        git(root, "tag", "3.1")
        return root

    return make


@pytest.fixture(name="git")
def git_fixture() -> Callable[..., None]:
    """The hermetic git helper, for tests."""
    return git
