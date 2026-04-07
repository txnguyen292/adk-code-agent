import pytest

from tools.docker.docker_sandbox import (
    DockerSandbox,
    DockerSandboxError,
    _normalize_cwd,
    _truncate,
)


def test_truncate_limits_output() -> None:
    value = "x" * 10
    out = _truncate(value, 4)
    assert out.startswith("xxxx")
    assert "truncated" in out


def test_rejects_long_command() -> None:
    sandbox = DockerSandbox()
    with pytest.raises(DockerSandboxError):
        sandbox.run_bash_sandbox("task1", "x" * 5000)


def test_rejects_invalid_cwd() -> None:
    sandbox = DockerSandbox()
    with pytest.raises(DockerSandboxError):
        sandbox.run_bash_sandbox("task1", "echo hi", cwd="/")


def test_rejects_disallowed_env() -> None:
    sandbox = DockerSandbox()
    with pytest.raises(DockerSandboxError):
        sandbox.run_bash_sandbox("task1", "echo hi", env={"AWS_SECRET_ACCESS_KEY": "x"})


def test_normalize_cwd_maps_relative_paths_into_work() -> None:
    assert _normalize_cwd(".") == "/work"
    assert _normalize_cwd("src") == "/work/src"
    assert _normalize_cwd("./src") == "/work/src"
