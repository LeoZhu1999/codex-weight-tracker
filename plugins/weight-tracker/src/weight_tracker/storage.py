from __future__ import annotations

import json
import os
import shutil
import time
from contextlib import contextmanager
from datetime import date, datetime, time as clock_time, timedelta
from pathlib import Path
from typing import Iterator
from uuid import uuid4
from zoneinfo import ZoneInfo

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo

from . import SCHEMA_VERSION
from .models import ChangeAction, ChangePatch, StoredRecord, TimeSource, WeightInput


HEADERS = ["record_id", "request_id", "measured_at", "timezone", "weight_kg", "time_source", "note", "created_at"]
AUDIT_HEADERS = ["event_id", "action", "record_id", "before_json", "after_json", "occurred_at", "request_id"]


class StorageError(RuntimeError):
    pass


class DuplicateRequest(StorageError):
    def __init__(self, record: StoredRecord):
        self.record = record
        super().__init__("This request was already recorded.")


class DuplicateCandidate(StorageError):
    def __init__(self, record: StoredRecord):
        self.record = record
        super().__init__("A record with the same time and weight already exists.")


class WorkbookLocked(StorageError):
    pass


@contextmanager
def exclusive_lock(path: Path, timeout_seconds: float = 4.0) -> Iterator[None]:
    lock_path = path.with_suffix(path.suffix + ".lock")
    deadline = time.monotonic() + timeout_seconds
    descriptor: int | None = None
    while time.monotonic() < deadline:
        try:
            descriptor = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(descriptor, str(os.getpid()).encode())
            break
        except FileExistsError:
            try:
                if time.time() - lock_path.stat().st_mtime > 120:
                    lock_path.unlink(missing_ok=True)
                    continue
            except FileNotFoundError:
                continue
            time.sleep(0.2)
    if descriptor is None:
        raise WorkbookLocked(f"Workbook is busy: {path}")
    try:
        yield
    finally:
        os.close(descriptor)
        lock_path.unlink(missing_ok=True)


def _make_table(sheet, name: str, ref: str) -> None:
    table = Table(displayName=name, ref=ref)
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    sheet.add_table(table)


def create_workbook(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "WeightLog"
    sheet.append(HEADERS)
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="0F766E")
    sheet.freeze_panes = "A2"
    sheet.sheet_view.showGridLines = False
    for column, width in {"A": 38, "B": 38, "C": 22, "D": 20, "E": 14, "F": 20, "G": 42, "H": 22}.items():
        sheet.column_dimensions[column].width = width
    _make_table(sheet, "WeightLog", "A1:H1")

    meta = workbook.create_sheet("_meta")
    meta.append(["key", "value"])
    meta.append(["schema_version", SCHEMA_VERSION])
    meta.append(["workbook_id", str(uuid4())])
    meta.append(["created_at", datetime.now().isoformat()])
    meta.sheet_state = "hidden"

    audit = workbook.create_sheet("_audit")
    audit.append(AUDIT_HEADERS)
    _make_table(audit, "AuditLog", "A1:G1")
    audit.sheet_state = "hidden"

    _save_atomic(workbook, path)


def _save_atomic(workbook, path: Path) -> None:
    temp = path.with_name(f".{path.stem}.{uuid4().hex}{path.suffix}")
    try:
        workbook.save(temp)
        check = load_workbook(temp, read_only=True, data_only=True)
        try:
            if "WeightLog" not in check.sheetnames:
                raise StorageError("Validation failed: WeightLog sheet is missing")
        finally:
            check.close()
        os.replace(temp, path)
    except PermissionError as exc:
        temp.unlink(missing_ok=True)
        raise WorkbookLocked(f"Close Excel before writing {path.name}") from exc


def _header_map(sheet) -> dict[str, int]:
    headers = [cell.value for cell in sheet[1]]
    if headers[: len(HEADERS)] != HEADERS:
        raise StorageError("Unsupported workbook schema. Run migration or restore a compatible workbook.")
    return {header: index + 1 for index, header in enumerate(headers)}


def _local_naive(value: datetime) -> datetime:
    return value.replace(tzinfo=None)


def _as_datetime(value, timezone_name: str) -> datetime:
    zone = ZoneInfo(timezone_name)
    if isinstance(value, datetime):
        return value.replace(tzinfo=zone) if value.tzinfo is None else value.astimezone(zone)
    raise StorageError("Workbook contains a non-datetime timestamp")


def _row_record(sheet, row: int, mapping: dict[str, int]) -> StoredRecord:
    timezone_name = sheet.cell(row, mapping["timezone"]).value
    measured = _as_datetime(sheet.cell(row, mapping["measured_at"]).value, timezone_name)
    created_raw = sheet.cell(row, mapping["created_at"]).value
    created = _as_datetime(created_raw, timezone_name) if isinstance(created_raw, datetime) else None
    return StoredRecord(
        record_id=str(sheet.cell(row, mapping["record_id"]).value),
        request_id=str(sheet.cell(row, mapping["request_id"]).value),
        measured_at=measured,
        timezone=str(timezone_name),
        weight_kg=float(sheet.cell(row, mapping["weight_kg"]).value),
        time_source=TimeSource(str(sheet.cell(row, mapping["time_source"]).value)),
        note=sheet.cell(row, mapping["note"]).value,
        created_at=created,
    )


def _update_table_ref(sheet, name: str, columns: int) -> None:
    table = sheet.tables[name]
    table.ref = f"A1:{chr(64 + columns)}{sheet.max_row}"


def _append_audit(sheet, action: str, record_id: str, before: StoredRecord | None, after: StoredRecord | None, request_id: str) -> None:
    sheet.append([
        f"audit_{uuid4().hex}", action, record_id,
        before.model_dump_json() if before else None,
        after.model_dump_json() if after else None,
        datetime.now().astimezone().replace(tzinfo=None), request_id,
    ])
    _update_table_ref(sheet, "AuditLog", len(AUDIT_HEADERS))


class ExcelStorage:
    def __init__(self, path: Path):
        self.path = path

    def ensure_exists(self) -> None:
        if not self.path.exists():
            create_workbook(self.path)

    def list_records(self, start: datetime | None = None, end: datetime | None = None) -> list[StoredRecord]:
        self.ensure_exists()
        workbook = load_workbook(self.path, read_only=True, data_only=True)
        try:
            sheet = workbook["WeightLog"]
            mapping = _header_map(sheet)
            records = [_row_record(sheet, row, mapping) for row in range(2, sheet.max_row + 1) if sheet.cell(row, 1).value]
        finally:
            workbook.close()
        records.sort(key=lambda item: item.measured_at)
        return [item for item in records if (start is None or item.measured_at >= start) and (end is None or item.measured_at <= end)]

    def append(self, item: WeightInput) -> StoredRecord:
        self.ensure_exists()
        with exclusive_lock(self.path):
            workbook = load_workbook(self.path)
            try:
                sheet = workbook["WeightLog"]
                mapping = _header_map(sheet)
                records = [_row_record(sheet, row, mapping) for row in range(2, sheet.max_row + 1) if sheet.cell(row, 1).value]
                for existing in records:
                    if existing.request_id == item.request_id:
                        raise DuplicateRequest(existing)
                    if not item.allow_duplicate and existing.measured_at == item.measured_at and abs(existing.weight_kg - item.weight_kg) < 0.0005:
                        raise DuplicateCandidate(existing)
                record = StoredRecord.from_input(item)
                sheet.append([
                    record.record_id, record.request_id, _local_naive(record.measured_at), record.timezone,
                    record.weight_kg, record.time_source.value, record.note,
                    _local_naive(record.created_at) if record.created_at else None,
                ])
                sheet.cell(sheet.max_row, mapping["measured_at"]).number_format = "yyyy-mm-dd hh:mm"
                sheet.cell(sheet.max_row, mapping["created_at"]).number_format = "yyyy-mm-dd hh:mm"
                _update_table_ref(sheet, "WeightLog", len(HEADERS))
                _save_atomic(workbook, self.path)
                return record
            finally:
                workbook.close()

    def get(self, record_id: str) -> StoredRecord:
        for record in self.list_records():
            if record.record_id == record_id:
                return record
        raise KeyError(record_id)

    def apply_change(self, action: ChangeAction, record_id: str, patch: ChangePatch | None, request_id: str) -> StoredRecord | None:
        with exclusive_lock(self.path):
            workbook = load_workbook(self.path)
            try:
                sheet = workbook["WeightLog"]
                mapping = _header_map(sheet)
                target_row = next((row for row in range(2, sheet.max_row + 1) if sheet.cell(row, mapping["record_id"]).value == record_id), None)
                if target_row is None:
                    raise KeyError(record_id)
                before = _row_record(sheet, target_row, mapping)
                audit = workbook["_audit"]
                if action is ChangeAction.DELETE:
                    sheet.delete_rows(target_row, 1)
                    _update_table_ref(sheet, "WeightLog", len(HEADERS))
                    _append_audit(audit, "delete", record_id, before, None, request_id)
                    _save_atomic(workbook, self.path)
                    return None
                if patch is None:
                    raise StorageError("An update requires a patch")
                data = before.model_dump()
                if patch.measured_at is not None:
                    data["measured_at"] = patch.measured_at
                if patch.timezone is not None:
                    data["timezone"] = patch.timezone
                if patch.weight_value is not None:
                    unit = patch.weight_unit.value if patch.weight_unit else "kg"
                    data["weight_kg"] = round(patch.weight_value if unit == "kg" else patch.weight_value * 0.45359237, 3)
                if patch.note is not None:
                    data["note"] = patch.note
                after = StoredRecord(**data)
                values = [after.record_id, after.request_id, _local_naive(after.measured_at), after.timezone, after.weight_kg, after.time_source.value, after.note, _local_naive(after.created_at) if after.created_at else None]
                for index, value in enumerate(values, 1):
                    sheet.cell(target_row, index).value = value
                _append_audit(audit, "update", record_id, before, after, request_id)
                _save_atomic(workbook, self.path)
                return after
            finally:
                workbook.close()


def _legacy_timestamp(day_value, time_value, timezone_name: str) -> datetime:
    if isinstance(day_value, datetime):
        day = day_value.date()
    elif isinstance(day_value, date):
        day = day_value
    else:
        raise StorageError("Legacy workbook contains an invalid date")
    if isinstance(time_value, datetime):
        moment = time_value.time()
    elif isinstance(time_value, clock_time):
        moment = time_value
    elif isinstance(time_value, timedelta):
        moment = (datetime.min + time_value).time()
    else:
        raise StorageError("Legacy workbook contains an invalid time")
    return datetime.combine(day, moment, tzinfo=ZoneInfo(timezone_name))


def migrate_legacy(source: Path, timezone_name: str, destination: Path | None = None) -> dict[str, object]:
    destination = destination or source
    legacy = load_workbook(source, read_only=True, data_only=True)
    try:
        sheet = legacy.active
        expected = ["日期", "时间", "体重 (kg)"]
        headers = [sheet.cell(1, index).value for index in range(1, 4)]
        if headers != expected:
            raise StorageError("Legacy workbook must have 日期, 时间, 体重 (kg) columns")
        rows = []
        for index, values in enumerate(sheet.iter_rows(min_row=2, max_col=3, values_only=True), start=2):
            if not values or values[0] is None:
                continue
            measured = _legacy_timestamp(values[0], values[1], timezone_name)
            rows.append((index, measured, float(values[2])))
    finally:
        legacy.close()
    if destination.exists():
        backup_dir = destination.parent / ".weight-tracker-backups"
        backup_dir.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = backup_dir / f"{destination.stem}.before-v1.{stamp}{destination.suffix}"
        shutil.copy2(destination, backup)
    else:
        backup = None
    temp_target = destination.with_name(f".{destination.stem}.migration-{uuid4().hex}{destination.suffix}")
    create_workbook(temp_target)
    storage = ExcelStorage(temp_target)
    for legacy_row, measured, weight in rows:
        storage.append(WeightInput(
            measured_at=measured, timezone=timezone_name, weight_value=weight, weight_unit="kg",
            time_source=TimeSource.LEGACY_IMPORT, note=None, request_id=f"legacy:{legacy_row}:{measured.isoformat()}:{weight}", allow_duplicate=True,
        ))
    os.replace(temp_target, destination)
    return {"records": len(rows), "backup": str(backup) if backup else None, "workbook": str(destination)}
