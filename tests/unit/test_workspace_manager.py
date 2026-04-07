from pathlib import Path
import subprocess

import pytest

from tools.agent.workspace_manager import WorkspaceError, WorkspaceManager


def test_workspace_path_validation(tmp_path: Path) -> None:
    manager = WorkspaceManager(tmp_path, tmp_path / "workspaces")
    with pytest.raises(WorkspaceError):
        manager._workspace_path("../bad")


def test_workspace_path_returns_expected_location(tmp_path: Path) -> None:
    manager = WorkspaceManager(tmp_path, tmp_path / "workspaces")
    assert manager.workspace_path("task1") == (tmp_path / "workspaces" / "task1")


def test_create_workspace_without_head_copies_snapshot(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True, text=True)
    (repo_root / ".gitignore").write_text("workspaces/*\n!workspaces/.gitkeep\n", encoding="utf-8")
    (repo_root / "README.md").write_text("hello\n", encoding="utf-8")

    manager = WorkspaceManager(repo_root, repo_root / "workspaces")
    workspace = manager.create_workspace("task1")

    assert workspace == repo_root / "workspaces" / "task1"
    assert (workspace / "README.md").read_text(encoding="utf-8") == "hello\n"
    assert not (workspace / ".git").exists()


def test_capture_diff_without_head_uses_snapshot_diff(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True, text=True)
    (repo_root / ".gitignore").write_text("workspaces/*\n!workspaces/.gitkeep\n", encoding="utf-8")
    (repo_root / "README.md").write_text("hello\n", encoding="utf-8")

    manager = WorkspaceManager(repo_root, repo_root / "workspaces")
    workspace = manager.create_workspace("task1")
    (workspace / "README.md").write_text("changed\n", encoding="utf-8")

    diff = manager.capture_diff("task1")

    assert "--- a/README.md" in diff
    assert "+++ b/README.md" in diff
    assert "-hello" in diff
    assert "+changed" in diff
