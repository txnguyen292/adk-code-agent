from __future__ import annotations

import posixpath
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping


class DockerSandboxError(RuntimeError):
    """Raised when sandbox setup or execution fails."""


@dataclass(slots=True)
class SandboxLimits:
    cpus: str = "2"
    memory: str = "2g"
    pids_limit: int = 256
    tmpfs_size: str = "512m"
    max_command_chars: int = 4096
    max_stdout_chars: int = 20_000
    max_stderr_chars: int = 20_000


@dataclass(slots=True)
class SandboxResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool = False


@dataclass(slots=True)
class DockerSandbox:
    image: str = "local-agent-env:latest"
    docker_binary: str = "docker"
    allowed_env_keys: set[str] = field(
        default_factory=lambda: {"PYTHONPATH", "PYTHONUNBUFFERED", "NODE_ENV", "CI"}
    )
    limits: SandboxLimits = field(default_factory=SandboxLimits)

    def create_task_container(self, task_id: str, workspace_path: str | Path) -> str:
        task_key = _validate_task_id(task_id)
        workspace = Path(workspace_path).resolve()
        if not workspace.exists() or not workspace.is_dir():
            raise DockerSandboxError(f"Workspace does not exist: {workspace}")

        container_name = self._container_name(task_key)

        create_cmd = [
            self.docker_binary,
            "create",
            "--name",
            container_name,
            "--network=none",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--read-only",
            "--tmpfs",
            f"/tmp:rw,noexec,nosuid,nodev,size={self.limits.tmpfs_size}",
            "--pids-limit",
            str(self.limits.pids_limit),
            "--cpus",
            self.limits.cpus,
            "--memory",
            self.limits.memory,
            "-v",
            f"{workspace}:/work:rw",
            "-w",
            "/work",
            "--user",
            "1000:1000",
            self.image,
            "sleep",
            "infinity",
        ]

        created = subprocess.run(create_cmd, capture_output=True, text=True, check=False)
        if created.returncode != 0:
            raise DockerSandboxError(created.stderr.strip() or "Failed to create sandbox container")

        started = subprocess.run(
            [self.docker_binary, "start", container_name], capture_output=True, text=True, check=False
        )
        if started.returncode != 0:
            raise DockerSandboxError(started.stderr.strip() or "Failed to start sandbox container")

        return container_name

    def run_bash_sandbox(
        self,
        task_id: str,
        command: str,
        cwd: str = "/work",
        timeout_s: int = 30,
        env: Mapping[str, str] | None = None,
    ) -> SandboxResult:
        task_key = _validate_task_id(task_id)
        if len(command) > self.limits.max_command_chars:
            raise DockerSandboxError(
                f"Command exceeds max length ({self.limits.max_command_chars} chars)"
            )
        cwd = _normalize_cwd(cwd)
        if not _is_safe_cwd(cwd):
            raise DockerSandboxError(f"cwd must stay within /work, got: {cwd}")

        container_name = self._container_name(task_key)
        safe_env = _filter_env(env or {}, self.allowed_env_keys)

        cmd = [self.docker_binary, "exec", "-w", cwd]
        for key, value in safe_env.items():
            cmd.extend(["-e", f"{key}={value}"])
        cmd.extend([container_name, "bash", "-lc", command])

        started = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
            )
            timed_out = False
            exit_code = proc.returncode
            stdout = proc.stdout
            stderr = proc.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            exit_code = 124
            stdout = exc.stdout or ""
            stderr = (exc.stderr or "") + "\nCommand timed out"
            subprocess.run(
                [self.docker_binary, "exec", container_name, "bash", "-lc", "pkill -f 'bash -lc' || true"],
                capture_output=True,
                text=True,
                check=False,
            )

        duration_ms = int((time.monotonic() - started) * 1000)
        return SandboxResult(
            exit_code=exit_code,
            stdout=_truncate(stdout, self.limits.max_stdout_chars),
            stderr=_truncate(stderr, self.limits.max_stderr_chars),
            duration_ms=duration_ms,
            timed_out=timed_out,
        )

    def destroy_task_container(self, task_id: str) -> None:
        task_key = _validate_task_id(task_id)
        container_name = self._container_name(task_key)
        subprocess.run(
            [self.docker_binary, "rm", "-f", container_name],
            capture_output=True,
            text=True,
            check=False,
        )

    @staticmethod
    def _container_name(task_id: str) -> str:
        return f"offline-agent-{task_id}"


def _validate_task_id(task_id: str) -> str:
    if not task_id or not re.fullmatch(r"[a-zA-Z0-9_.-]{1,64}", task_id):
        raise DockerSandboxError(
            "task_id must match [a-zA-Z0-9_.-] and be 1-64 chars"
        )
    return task_id


def _filter_env(env: Mapping[str, str], allowed_keys: set[str]) -> dict[str, str]:
    filtered: dict[str, str] = {}
    for key, value in env.items():
        if key not in allowed_keys:
            raise DockerSandboxError(f"Environment key is not allowlisted: {key}")
        filtered[key] = value
    return filtered


def _normalize_cwd(cwd: str) -> str:
    if not cwd or cwd == ".":
        return "/work"
    if cwd.startswith("/"):
        return posixpath.normpath(cwd)
    return posixpath.normpath(posixpath.join("/work", cwd))


def _is_safe_cwd(cwd: str) -> bool:
    if not cwd.startswith("/work"):
        return False
    disallowed = ["..", "~", "//"]
    return not any(token in cwd for token in disallowed)


def _truncate(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    kept = value[:max_chars]
    return f"{kept}\n... [truncated]"
