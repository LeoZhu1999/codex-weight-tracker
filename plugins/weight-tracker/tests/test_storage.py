from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from openpyxl import Workbook, load_workbook

from weight_tracker.models import ChangeAction, ChangePatch, TimeSource, WeightInput
from weight_tracker.storage import DuplicateRequest, ExcelStorage, migrate_legacy


def item(request_id="request-0001", value=83.5):
    return WeightInput(
        measured_at=datetime(2026, 11, 18, 8, 30, tzinfo=ZoneInfo("Europe/Berlin")), timezone="Europe/Berlin",
        weight_value=value, weight_unit="kg", time_source=TimeSource.USER_PROVIDED, request_id=request_id,
    )


def test_append_is_idempotent_and_auditable(tmp_path: Path):
    storage = ExcelStorage(tmp_path / "records.xlsx")
    first = storage.append(item())
    assert storage.list_records()[0].weight_kg == 83.5
    with pytest.raises(DuplicateRequest):
        storage.append(item())
    changed = storage.apply_change(ChangeAction.UPDATE, first.record_id, ChangePatch(weight_value=83.6, weight_unit="kg"), "change-request")
    assert changed.weight_kg == 83.6
    workbook = load_workbook(tmp_path / "records.xlsx", data_only=True)
    assert workbook["_audit"].max_row == 2
    workbook.close()


def test_migrate_legacy_three_column_workbook(tmp_path: Path):
    legacy = tmp_path / "legacy.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["日期", "时间", "体重 (kg)"])
    sheet.append([datetime(2026, 11, 17), datetime(1899, 12, 30, 8, 20), 83.8])
    workbook.save(legacy)
    result = migrate_legacy(legacy, "Europe/Berlin")
    assert result["records"] == 1
    assert result["backup"]
    storage = ExcelStorage(legacy)
    assert storage.list_records()[0].time_source is TimeSource.LEGACY_IMPORT
