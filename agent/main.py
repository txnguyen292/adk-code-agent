from __future__ import annotations

import argparse
from agent.agent import OfflineCodingAgent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline coding agent runner")
    parser.add_argument("--repo", default=".", help="Path to the base git repository")

    subparsers = parser.add_subparsers(dest="cmd", required=True)

    start = subparsers.add_parser("start-task")
    start.add_argument("task_id")
    start.add_argument("--ref", default="HEAD")

    run = subparsers.add_parser("run")
    run.add_argument("task_id")
    run.add_argument("command")
    run.add_argument("--timeout", type=int, default=30)

    stop = subparsers.add_parser("stop-task")
    stop.add_argument("task_id")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    agent = OfflineCodingAgent(args.repo)

    if args.cmd == "start-task":
        agent.start_task(args.task_id, ref=args.ref)
        return
    if args.cmd == "run":
        result = agent.run_command(args.task_id, args.command, timeout_s=args.timeout)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return
    if args.cmd == "stop-task":
        agent.stop_task(args.task_id)
        return


if __name__ == "__main__":
    main()
