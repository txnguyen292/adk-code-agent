from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from core.llm import OpenAIConfig
from tools.agent.file_tools import FileTools
from tools.agent.task_logger import TaskLogger
from tools.agent.adk_tools import build_adk_tools
from tools.agent.workspace_manager import WorkspaceManager
from tools.docker.docker_sandbox import DockerSandbox, SandboxResult


DEFAULT_REPO_ROOT = Path(
    os.environ.get("OFFLINE_AGENT_REPO", str(Path(__file__).resolve().parents[1]))
).resolve()

AGENT_INSTRUCTION = """
You are an offline coding agent that must execute shell commands through the
sandboxed bash tool only.

Rules:
- Inspect the repository before making edits.
- Prefer running tests after edits.
- Never attempt host-level shell access.
- Summarize final changes with commands run and test results.
""".strip()


class ADKBridgeError(RuntimeError):
    """Raised when ADK integration cannot be initialized."""


class OfflineCodingAgent:
    def __init__(self, repo_root: str | Path):
        self.repo_root = Path(repo_root).resolve()
        self.project_root = self.repo_root
        self.log_root = self.project_root / "logs"
        self.workspace_manager = WorkspaceManager(
            repo_root=self.repo_root,
            workspaces_root=self.project_root / "workspaces",
        )
        self.sandbox = DockerSandbox()
        self.logger = TaskLogger(self.log_root)

    def start_task(self, task_id: str, ref: str = "HEAD") -> None:
        workspace = self.workspace_manager.create_workspace(task_id, ref=ref)
        container = self.sandbox.create_task_container(task_id, workspace)
        self.logger.log_event(
            task_id,
            "task_started",
            {"workspace": str(workspace), "container": container, "ref": ref},
        )

    def run_command(
        self,
        task_id: str,
        command: str,
        timeout_s: int = 30,
        cwd: str = "/work",
        env: dict[str, str] | None = None,
    ) -> SandboxResult:
        result = self.sandbox.run_bash_sandbox(
            task_id,
            command=command,
            timeout_s=timeout_s,
            cwd=cwd,
            env=env,
        )
        self.logger.log_event(
            task_id,
            "command_executed",
            {
                "command": command,
                "exit_code": result.exit_code,
                "duration_ms": result.duration_ms,
                "timed_out": result.timed_out,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "cwd": cwd,
                "env_keys": sorted((env or {}).keys()),
            },
        )
        return result

    def file_tools_for_task(self, task_id: str) -> FileTools:
        workspace = self.workspace_manager.workspace_path(task_id)
        if not workspace.exists():
            raise RuntimeError(f"Workspace does not exist for task: {task_id}")
        return FileTools(workspace)

    def stop_task(self, task_id: str) -> None:
        diff = self.workspace_manager.capture_diff(task_id)
        diff_file = self.log_root / f"{task_id}_diff.patch"
        diff_file.write_text(diff, encoding="utf-8")

        self.sandbox.destroy_task_container(task_id)
        self.workspace_manager.remove_workspace(task_id)
        self.logger.log_event(task_id, "task_stopped", {"diff_file": str(diff_file)})


def build_root_agent(
    repo_root: str | Path = DEFAULT_REPO_ROOT,
    model: str | None = None,
) -> Any:
    try:
        from google.adk.agents.llm_agent import Agent
        from google.adk.models.lite_llm import LiteLlm
    except ImportError as exc:
        raise ADKBridgeError(
            "google-adk[extensions] is required for LiteLLM/OpenAI support. Run `uv sync` and retry."
        ) from exc

    config = OpenAIConfig.from_env()
    if model:
        config.model = model
    config.apply()

    runtime = OfflineCodingAgent(repo_root)
    return Agent(
        name="offline_coding_agent",
        model=LiteLlm(
            model=config.litellm_model(),
            temperature=config.effective_temperature(),
            drop_params=config.drop_params_enabled(),
        ),
        description="Offline coding agent with docker-sandboxed bash execution",
        instruction=AGENT_INSTRUCTION,
        tools=build_adk_tools(runtime),
    )


def build_app(
    repo_root: str | Path = DEFAULT_REPO_ROOT,
    model: str | None = None,
    root_agent_obj: Any | None = None,
) -> Any:
    try:
        from google.adk.apps import App
    except ImportError as exc:
        raise ADKBridgeError(
            "google-adk[extensions] is required for LiteLLM/OpenAI support. Run `uv sync` and retry."
        ) from exc

    return App(
        name="agent",
        root_agent=root_agent_obj or build_root_agent(repo_root, model),
    )


ROOT_AGENT_INIT_ERROR: str | None = None
APP_INIT_ERROR: str | None = None
root_agent: Any | None = None
app: Any | None = None

try:
    root_agent = build_root_agent()
    app = build_app(root_agent_obj=root_agent)
except ADKBridgeError as exc:
    ROOT_AGENT_INIT_ERROR = str(exc)
    APP_INIT_ERROR = str(exc)
