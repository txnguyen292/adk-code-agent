from __future__ import annotations

import difflib
import shutil
import subprocess
from pathlib import Path


class WorkspaceError(RuntimeError):
    """Raised when workspace lifecycle operations fail."""


class WorkspaceManager:
    def __init__(self, repo_root: str | Path, workspaces_root: str | Path):
        self.repo_root = Path(repo_root).resolve()
        self.workspaces_root = Path(workspaces_root).resolve()
        self.workspaces_root.mkdir(parents=True, exist_ok=True)

    def create_workspace(self, task_id: str, ref: str = "HEAD") -> Path:
        workspace_path = self._workspace_path(task_id)
        if workspace_path.exists():
            raise WorkspaceError(f"Workspace already exists: {workspace_path}")

        if ref == "HEAD" and not self._has_head():
            self._copy_workspace_snapshot(workspace_path)
            return workspace_path

        cmd = [
            "git",
            "-C",
            str(self.repo_root),
            "worktree",
            "add",
            "--detach",
            str(workspace_path),
            ref,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise WorkspaceError(proc.stderr.strip() or "Failed to create workspace")

        return workspace_path

    def workspace_path(self, task_id: str) -> Path:
        return self._workspace_path(task_id)

    def remove_workspace(self, task_id: str) -> None:
        workspace_path = self._workspace_path(task_id)
        if not workspace_path.exists():
            return

        if not (workspace_path / ".git").exists():
            shutil.rmtree(workspace_path)
            return

        remove_cmd = [
            "git",
            "-C",
            str(self.repo_root),
            "worktree",
            "remove",
            "--force",
            str(workspace_path),
        ]
        remove_proc = subprocess.run(remove_cmd, capture_output=True, text=True, check=False)
        if remove_proc.returncode != 0:
            raise WorkspaceError(remove_proc.stderr.strip() or "Failed to remove workspace")

        subprocess.run(
            ["git", "-C", str(self.repo_root), "worktree", "prune"],
            capture_output=True,
            text=True,
            check=False,
        )

    def capture_diff(self, task_id: str) -> str:
        workspace_path = self._workspace_path(task_id)
        if not workspace_path.exists():
            raise WorkspaceError(f"Workspace does not exist: {workspace_path}")

        if not (workspace_path / ".git").exists():
            return self._diff_snapshot_workspace(workspace_path)

        cmd = ["git", "-C", str(workspace_path), "diff"]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise WorkspaceError(proc.stderr.strip() or "Failed to capture diff")
        return proc.stdout

    def _has_head(self) -> bool:
        proc = subprocess.run(
            ["git", "-C", str(self.repo_root), "rev-parse", "--verify", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.returncode == 0

    def _copy_workspace_snapshot(self, workspace_path: Path) -> None:
        workspace_path.mkdir(parents=True, exist_ok=False)
        for relative_path in self._repo_snapshot_files():
            source = self.repo_root / relative_path
            target = workspace_path / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    def _repo_snapshot_files(self) -> list[Path]:
        proc = subprocess.run(
            [
                "git",
                "-C",
                str(self.repo_root),
                "ls-files",
                "-z",
                "--cached",
                "--others",
                "--exclude-standard",
            ],
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            stderr = proc.stderr.decode("utf-8", errors="replace").strip()
            raise WorkspaceError(stderr or "Failed to enumerate repository files")

        raw_paths = [item for item in proc.stdout.split(b"\x00") if item]
        return sorted(Path(item.decode("utf-8")) for item in raw_paths)

    def _diff_snapshot_workspace(self, workspace_path: Path) -> str:
        repo_files = {path.as_posix() for path in self._repo_snapshot_files()}
        workspace_files = {
            path.relative_to(workspace_path).as_posix()
            for path in workspace_path.rglob("*")
            if path.is_file()
        }

        diff_chunks: list[str] = []
        for relative_name in sorted(repo_files | workspace_files):
            rel_path = Path(relative_name)
            repo_file = self.repo_root / rel_path
            workspace_file = workspace_path / rel_path

            repo_lines = self._read_lines(repo_file) if relative_name in repo_files else []
            workspace_lines = (
                self._read_lines(workspace_file) if relative_name in workspace_files else []
            )

            if repo_lines == workspace_lines:
                continue

            diff_chunks.extend(
                difflib.unified_diff(
                    repo_lines,
                    workspace_lines,
                    fromfile=f"a/{relative_name}",
                    tofile=f"b/{relative_name}",
                    lineterm="",
                )
            )

        if not diff_chunks:
            return ""
        return "\n".join(diff_chunks) + "\n"

    @staticmethod
    def _read_lines(path: Path) -> list[str]:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()

    def _workspace_path(self, task_id: str) -> Path:
        if not task_id or "/" in task_id or ".." in task_id:
            raise WorkspaceError("Invalid task_id")
        return self.workspaces_root / task_id
