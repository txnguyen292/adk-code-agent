# Offline Coding Agent Decisions

- Agent framework: `google-adk` with explicit tool registration.
- Tool layout: agent-side helpers live under `tools/agent/`; container execution lives under `tools/docker/`.
- Container lifetime: persistent per task (`docker create` + `docker exec` + `docker rm`).
- Network policy: disabled by default (`--network=none`).
- Sandbox user: non-root user `agent` (`uid:gid = 1000:1000`).
- Workspace model: isolated per-task git worktree under `workspaces/`.
- Toolchains preinstalled in image: Python + Node + git + ripgrep.
- Filesystem policy: container root filesystem read-only, writable `/work` mount + tmpfs `/tmp`.
- Resource defaults: 2 CPUs, 2 GB memory, 256 PIDs, 30s command timeout.
