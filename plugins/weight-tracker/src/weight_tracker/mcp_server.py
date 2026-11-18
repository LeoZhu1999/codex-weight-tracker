from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .config import load_config
from .dashboard import DashboardServer
from .models import ChangeAction
from .service import WeightService
from .storage import DuplicateCandidate, DuplicateRequest, StorageError, WorkbookLocked


mcp = FastMCP("Codex Weight Tracker")


def _service() -> WeightService:
    return WeightService(load_config())


def _record_payload(record):
    return record.model_dump(mode="json")


@mcp.tool()
def record_weight(
    measured_at: datetime,
    timezone: str,
    weight_value: float,
    weight_unit: str,
    time_source: str,
    request_id: str,
    note: str | None = None,
    allow_duplicate: bool = False,
) -> dict:
    """Store a body-weight measurement. measured_at must include a UTC offset."""
    try:
        record = _service().record_weight(
            measured_at=measured_at, timezone=timezone, weight_value=weight_value, weight_unit=weight_unit,
            time_source=time_source, request_id=request_id, note=note, allow_duplicate=allow_duplicate,
        )
        return {"status": "created", "record": _record_payload(record)}
    except DuplicateRequest as exc:
        return {"status": "already_recorded", "record": _record_payload(exc.record)}
    except DuplicateCandidate as exc:
        return {"status": "duplicate_candidate", "record": _record_payload(exc.record), "message": str(exc)}
    except (StorageError, ValueError) as exc:
        return {"status": "error", "message": str(exc)}


@mcp.tool()
def list_weight_records(start: datetime | None = None, end: datetime | None = None) -> dict:
    """List stored raw measurements, optionally constrained by offset-aware timestamps."""
    try:
        records = _service().list_records(start, end)
        return {"status": "ok", "records": [_record_payload(item) for item in records]}
    except (StorageError, ValueError) as exc:
        return {"status": "error", "message": str(exc)}


@mcp.tool()
def prepare_weight_change(action: str, record_id: str, request_id: str, patch: dict | None = None) -> dict:
    """Preview one update or deletion. Show the preview to the user and obtain explicit confirmation before commit_weight_change."""
    try:
        change = _service().prepare_change(ChangeAction(action), record_id, patch, request_id)
        before = _service().storage.get(record_id)
        return {"status": "confirmation_required", "before": _record_payload(before), "action": change.action.value, "patch": change.patch.model_dump(mode="json") if change.patch else None, "confirmation_token": change.token, "expires_at": change.expires_at.isoformat()}
    except (KeyError, StorageError, ValueError) as exc:
        return {"status": "error", "message": str(exc)}


@mcp.tool()
def commit_weight_change(confirmation_token: str, request_id: str) -> dict:
    """Commit the one-time update or deletion after the user explicitly confirmed the preview."""
    try:
        record = _service().commit_change(confirmation_token, request_id)
        return {"status": "deleted" if record is None else "updated", "record": _record_payload(record) if record else None}
    except (KeyError, StorageError, ValueError) as exc:
        return {"status": "error", "message": str(exc)}


@mcp.tool()
def get_dashboard_url() -> dict:
    """Start the local read-only browser dashboard and return its loopback URL."""
    try:
        config = load_config()
        return {"status": "ok", "url": DashboardServer.start(config)}
    except (StorageError, ValueError, FileNotFoundError) as exc:
        return {"status": "error", "message": str(exc)}


@mcp.tool()
def health_check() -> dict:
    """Check local configuration and the workbook without modifying records."""
    try:
        config = load_config()
        records = WeightService(config).list_records()
        return {"status": "ok", "workbook": str(Path(config.workbook_path)), "records": len(records), "timezone": config.timezone, "height_cm": config.height_cm, "bmi_standard": config.bmi_standard}
    except Exception as exc:
        print(f"Weight Tracker health check failed: {exc}", file=sys.stderr)
        return {"status": "error", "message": str(exc)}


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
