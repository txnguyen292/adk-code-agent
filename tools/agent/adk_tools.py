from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent.agent import OfflineCodingAgent


def build_adk_tools(runtime: OfflineCodingAgent) -> list[Any]:
    def start_task(task_id: str, ref: str = "HEAD") -> dict[str, Any]:
        runtime.start_task(task_id=task_id, ref=ref)
        workspace = runtime.workspace_manager.workspace_path(task_id)
        return {"task_id": task_id, "workspace": str(workspace), "ref": ref}

    def bash_tool(
        task_id: str,
        command: str,
        timeout_s: int = 30,
        cwd: str = "/work",
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        result = runtime.run_command(
            task_id=task_id,
            command=command,
            timeout_s=timeout_s,
            cwd=cwd,
            env=env,
        )
        return {
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration_ms": result.duration_ms,
            "timed_out": result.timed_out,
        }

    def read_file(task_id: str, path: str) -> str:
        return runtime.file_tools_for_task(task_id).read_file(path)

    def write_file(task_id: str, path: str, content: str) -> dict[str, str]:
        runtime.file_tools_for_task(task_id).write_file(path, content)
        return {"status": "ok", "path": path}

    def list_dir(task_id: str, path: str = ".") -> list[str]:
        return runtime.file_tools_for_task(task_id).list_dir(path)

    def search(task_id: str, query: str, path: str = ".") -> list[str]:
        return runtime.file_tools_for_task(task_id).search(query=query, path=path)

    def stop_task(task_id: str) -> dict[str, str]:
        runtime.stop_task(task_id)
        diff_file = runtime.log_root / f"{task_id}_diff.patch"
        return {"status": "stopped", "task_id": task_id, "diff_file": str(diff_file)}

    return [start_task, bash_tool, read_file, write_file, list_dir, search, stop_task]
