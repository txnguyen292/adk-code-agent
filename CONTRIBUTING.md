# Contributing

## Setup

Use `uv` for local development.

```bash
uv sync
source .venv/bin/activate
```

The agent runtime uses OpenAI via LiteLLM. Set an API key before running the ADK app:

```bash
export OPENAI_API_KEY="your_openai_api_key"
export OPENAI_MODEL="gpt-5.4"
```

## Development Workflow

- Keep changes scoped and easy to verify.
- Run tests before pushing.
- Prefer updating or adding focused unit tests alongside behavior changes.
- Do not commit runtime artifacts such as `.adk/`, `logs/*.jsonl`, or workspace outputs.

## Common Commands

Run the unit test suite:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q
```

Start the ADK CLI:

```bash
adk run agent
```

Start the ADK web UI:

```bash
adk web . --port 8000
```

Run the local sandbox CLI directly:

```bash
python -m agent.main --repo . start-task demo
python -m agent.main --repo . run demo "rg --files"
python -m agent.main --repo . stop-task demo
```

## CI Expectations

GitHub Actions runs:

- dependency install with `uv`
- unit tests with `pytest`
- a small import smoke test for `agent.agent`

Keep those checks green before opening or updating a branch.
