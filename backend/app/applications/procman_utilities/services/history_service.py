
import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings


class HistoryService:
    def __init__(self):
        self.output_dir = Path(settings.OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.history_file = (
            self.output_dir / "procman_comparison_history.json"
        )

        self._lock = threading.Lock()

    def _load_history(self) -> list[dict[str, Any]]:
        if not self.history_file.exists():
            return []

        try:
            data = json.loads(
                self.history_file.read_text(encoding="utf-8")
            )

            if not isinstance(data, list):
                raise ValueError("Invalid comparison history format.")

            return data

        except json.JSONDecodeError as exc:
            raise ValueError(
                "Comparison history file contains invalid JSON."
            ) from exc

    def _save_history(self, records: list[dict[str, Any]]) -> None:
        temporary_file = self.history_file.with_suffix(".tmp")

        temporary_file.write_text(
            json.dumps(records, indent=4, ensure_ascii=False),
            encoding="utf-8",
        )

        temporary_file.replace(self.history_file)

    def create_record(
        self,
        *,
        page_id: str,
        page_name: str,
        source_version: str,
        target_version: str,
        status: str,
        report_path: str | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:

        if status not in {"success", "failed"}:
            raise ValueError(
                "Status must be either 'success' or 'failed'."
            )

        record = {
            "id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "page_id": page_id,
            "page_name": page_name,
            "source_version": source_version,
            "target_version": target_version,
            "status": status,
            "report_path": report_path,
            "error": error,
        }

        with self._lock:
            records = self._load_history()
            records.insert(0, record)
            self._save_history(records)

        return record

    def get_all_records(self) -> list[dict[str, Any]]:
        with self._lock:
            return self._load_history()

    def get_record(self, record_id: str) -> dict[str, Any] | None:
        with self._lock:
            records = self._load_history()

            return next(
                (
                    record
                    for record in records
                    if record.get("id") == record_id
                ),
                None,
            )

    def get_report_path(self, record_id: str) -> Path | None:
        record = self.get_record(record_id)

        if not record or not record.get("report_path"):
            return None

        report_path = Path(record["report_path"])

        if not report_path.is_file():
            return None

        return report_path


history_service = HistoryService()
