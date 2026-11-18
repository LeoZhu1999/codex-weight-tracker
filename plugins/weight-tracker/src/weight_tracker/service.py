from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from .config import AppConfig
from .models import ChangeAction, ChangePatch, PendingChange, WeightInput
from .storage import ExcelStorage, StorageError


class WeightService:
    def __init__(self, config: AppConfig):
        self.config = config
        self.storage = ExcelStorage(Path(config.workbook_path))
        self.pending_path = config.data_dir / "pending_changes.json"

    def record_weight(self, **payload):
        return self.storage.append(WeightInput(**payload))

    def list_records(self, start: datetime | None = None, end: datetime | None = None):
        return self.storage.list_records(start, end)

    def prepare_change(self, action: ChangeAction, record_id: str, patch: dict | None, request_id: str) -> PendingChange:
        record = self.storage.get(record_id)
        parsed_patch = ChangePatch(**patch) if patch else None
        if action is ChangeAction.UPDATE and parsed_patch is None:
            raise StorageError("Update requires at least one changed field")
        pending = PendingChange(
            token=f"chg_{uuid4().hex}", action=action, record_id=record_id, patch=parsed_patch,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
        entries = self._load_pending()
        entries[pending.token] = {"pending": pending.model_dump(mode="json"), "request_id": request_id, "before": record.model_dump(mode="json")}
        self._save_pending(entries)
        return pending

    def commit_change(self, token: str, request_id: str):
        entries = self._load_pending()
        entry = entries.pop(token, None)
        self._save_pending(entries)
        if entry is None:
            raise StorageError("Confirmation token is missing, expired, or already used")
        pending = PendingChange.model_validate(entry["pending"])
        if pending.expires_at < datetime.now(timezone.utc):
            raise StorageError("Confirmation token has expired")
        return self.storage.apply_change(pending.action, pending.record_id, pending.patch, request_id)

    def _load_pending(self) -> dict:
        if not self.pending_path.exists():
            return {}
        return json.loads(self.pending_path.read_text(encoding="utf-8"))

    def _save_pending(self, entries: dict) -> None:
        self.pending_path.parent.mkdir(parents=True, exist_ok=True)
        self.pending_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
