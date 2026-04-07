# Offline Coding Agent

A local coding agent that uses `google-adk` for orchestration and executes every shell command inside a locked-down Docker sandbox.

## What is included

- `Dockerfile` with preinstalled toolchain (`python3`, `nodejs`, `git`, `ripgrep`).
- `agent/agent.py` with the core runtime plus ADK-standard `root_agent` and `app` definitions.
- Persistent per-task sandbox model (`docker create` + `docker exec`).
- Workspace isolation via `git worktree`.
- Guardrailed bash execution tool.
- Safe file tools and JSONL task logging.
- Initial unit tests.

## Project layout

- `agent/`: runtime class, ADK entrypoint, and CLI entrypoint
- `tools/agent/`: ADK tool registration, workspace manager, file tools, task logging
- `tools/docker/`: Docker sandbox implementation
- `workspaces/`: per-task isolated worktrees
- `logs/`: JSONL traces and patch outputs
- `tests/`: unit tests

## Install dependencies

```bash
uv sync
```

This project requires `google-adk[extensions]` so ADK can load `LiteLlm` for OpenAI-backed models.

## Build sandbox image

```bash
docker build -t local-agent-env:latest .
```

## Quick start

```bash
python -m agent.main --repo /path/to/target/repo start-task task1
python -m agent.main --repo /path/to/target/repo run task1 "rg --files"
python -m agent.main --repo /path/to/target/repo stop-task task1
```

## ADK usage

`agent/agent.py` defines both `root_agent` and `app`, which matches ADK's documented Python layout.

- `bash_tool(task_id, command, timeout_s=30, cwd="/work", env=None)`
- `read_file(task_id, path)`
- `write_file(task_id, path, content)`
- `list_dir(task_id, path=".")`
- `search(task_id, query, path=".")`

Example:

```python
from agent.agent import app, build_app, build_root_agent, root_agent

agent = root_agent
application = app
```

## Model configuration

This agent mirrors the LiteLLM/OpenAI configuration pattern from the CEF discovery project and uses ADK's `LiteLlm` wrapper on top of it.

- Default model: `gpt-5.4`
- LiteLLM model resolution: `gpt-5.4` becomes `openai/gpt-5.4`
- Default auth env var: `OPENAI_API_KEY`
- Optional env vars: `OPENAI_MODEL`, `OPENAI_BASE_URL` or `OPENAI_API_BASE`, `OPENAI_TEMPERATURE`
- Backward-compatible alias: `OFFLINE_AGENT_MODEL`

Example:

```bash
export OPENAI_API_KEY="your_openai_api_key"
export OPENAI_MODEL="gpt-5.4"
export OPENAI_BASE_URL="https://us.api.openai.com/v1"
export OPENAI_TEMPERATURE="0.2"
```

## Run the agent

```bash
cd /Users/gt132601/Desktop/gainwell/offline-coding-agent
uv sync
export OPENAI_API_KEY="your_openai_api_key"
adk run agent
```

For the web UI:

```bash
cd /Users/gt132601/Desktop/gainwell/offline-coding-agent
uv sync
export OPENAI_API_KEY="your_openai_api_key"
adk web . --port 8000
```

## Notes

- Network is disabled in the sandbox by default.
- Container runs as non-root user `1000:1000`.
- Root filesystem is read-only; only `/work` is writable.
- If `google-adk[extensions]` is not installed in the active environment, `root_agent` and `app` are `None`, and the init error fields explain why.
