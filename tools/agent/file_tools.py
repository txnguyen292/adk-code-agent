from __future__ import annotations

import os
import tempfile
from pathlib import Path


class FileToolError(RuntimeError):
    """Raised when a file operation violates workspace policy."""


class FileTools:
    def __init__(self, workspace_root: str | Path):
        self.workspace_root = Path(workspace_root).resolve()

    def read_file(self, path: str) -> str:
        target = self._resolve(path)
        if not target.exists() or not target.is_file():
            raise FileToolError(f"File not found: {target}")
        return target.read_text(encoding="utf-8")

    def write_file(self, path: str, content: str) -> None:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=target.parent, delete=False
        ) as temp_file:
            temp_file.write(content)
            tmp_name = temp_file.name

        os.replace(tmp_name, target)

    def list_dir(self, path: str = ".") -> list[str]:
        target = self._resolve(path)
        if not target.exists() or not target.is_dir():
            raise FileToolError(f"Directory not found: {target}")
        return sorted(entry.name for entry in target.iterdir())

    def search(self, query: str, path: str = ".") -> list[str]:
        target = self._resolve(path)
        if not target.exists():
            raise FileToolError(f"Path not found: {target}")

        results: list[str] = []
        for file_path in target.rglob("*"):
            if not file_path.is_file():
                continue
            try:
                text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for line_number, line in enumerate(text.splitlines(), start=1):
                if query in line:
                    rel = file_path.relative_to(self.workspace_root)
                    results.append(f"{rel}:{line_number}:{line}")
        return results

    def _resolve(self, path: str) -> Path:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = self.workspace_root / candidate

        resolved = candidate.resolve()
        if resolved != self.workspace_root and self.workspace_root not in resolved.parents:
            raise FileToolError(f"Path escapes workspace root: {path}")
        return resolved
