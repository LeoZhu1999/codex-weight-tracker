from datetime import datetime
from zoneinfo import ZoneInfo

from weight_tracker.analytics import bmi_category, daily_dashboard
from weight_tracker.models import StoredRecord, TimeSource


def record(record_id: str, day: int, weight: float):
    timestamp = datetime(2026, 11, day, 8, 0, tzinfo=ZoneInfo("Europe/Berlin"))
    return StoredRecord(record_id=record_id, request_id=record_id, measured_at=timestamp, timezone="Europe/Berlin", weight_kg=weight, time_source=TimeSource.USER_PROVIDED, created_at=timestamp)


def test_daily_average_and_seven_day_change():
    items = [record("a", 1, 84.0), record("b", 1, 83.0)] + [record(str(day), day, 83.0 - day / 10) for day in range(2, 10)]
    dashboard = daily_dashboard(items, "Europe/Berlin", 176, "china_adult", "kg")
    assert dashboard["points"][0]["weight"] == 83.5
    assert dashboard["latest"]["weight"] == 82.1
    assert dashboard["seven_day_change"] is not None


def test_bmi_boundaries():
    assert bmi_category(23.9, "china_adult") == "Normal"
    assert bmi_category(24.0, "china_adult") == "Overweight"
    assert bmi_category(25.0, "who_adult") == "Overweight"
