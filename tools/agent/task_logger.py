from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class TaskLogger:
    def __init__(self, log_root: str | Path):
        self.log_root = Path(log_root)
        self.log_root.mkdir(parents=True, exist_ok=True)

    def log_event(self, task_id: str, event: str, payload: dict[str, Any]) -> None:
        file_path = self.log_root / f"{task_id}.jsonl"
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "task_id": task_id,
            "event": event,
            "payload": payload,
        }
        with file_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")
