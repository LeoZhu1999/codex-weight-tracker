from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from .models import StoredRecord


def bmi_category(value: float, standard: str) -> str:
    if standard == "china_adult":
        if value < 18.5:
            return "Underweight"
        if value < 24:
            return "Normal"
        if value < 28:
            return "Overweight"
        return "Obesity"
    if value < 18.5:
        return "Underweight"
    if value < 25:
        return "Normal"
    if value < 30:
        return "Overweight"
    return "Obesity"


def daily_dashboard(records: list[StoredRecord], timezone_name: str, height_cm: float, bmi_standard: str, display_unit: str) -> dict:
    zone = ZoneInfo(timezone_name)
    grouped: dict[date, list[float]] = defaultdict(list)
    for record in records:
        grouped[record.measured_at.astimezone(zone).date()].append(record.weight_kg)
    points = []
    for day in sorted(grouped):
        points.append({"date": day.isoformat(), "weight_kg": round(sum(grouped[day]) / len(grouped[day]), 3), "measurements": len(grouped[day])})
    lookup = {date.fromisoformat(point["date"]): point["weight_kg"] for point in points}
    for point in points:
        day = date.fromisoformat(point["date"])
        window = [lookup[candidate] for candidate in (day - timedelta(days=offset) for offset in range(7)) if candidate in lookup]
        point["rolling_7d_kg"] = round(sum(window) / len(window), 3) if window else None
        point["rolling_7d_days"] = len(window)
    latest = points[-1] if points else None
    seven_day_change = None
    if latest:
        latest_day = date.fromisoformat(latest["date"])
        current = [lookup[candidate] for candidate in (latest_day - timedelta(days=offset) for offset in range(7)) if candidate in lookup]
        previous = [lookup[candidate] for candidate in (latest_day - timedelta(days=offset) for offset in range(7, 14)) if candidate in lookup]
        if current and previous:
            seven_day_change = {
                "kg": round(sum(current) / len(current) - sum(previous) / len(previous), 3),
                "current_days": len(current), "previous_days": len(previous),
            }
    height_m = height_cm / 100
    bmi = round(latest["weight_kg"] / (height_m * height_m), 1) if latest and height_m > 0 else None
    conversion = 2.2046226218
    if display_unit == "lb":
        for point in points:
            point["weight"] = round(point["weight_kg"] * conversion, 2)
            point["rolling_7d"] = round(point["rolling_7d_kg"] * conversion, 2) if point["rolling_7d_kg"] is not None else None
        if seven_day_change:
            seven_day_change["display"] = round(seven_day_change["kg"] * conversion, 2)
    else:
        for point in points:
            point["weight"] = point["weight_kg"]
            point["rolling_7d"] = point["rolling_7d_kg"]
        if seven_day_change:
            seven_day_change["display"] = seven_day_change["kg"]
    return {
        "unit": display_unit,
        "points": points,
        "latest": latest,
        "bmi": {"value": bmi, "category": bmi_category(bmi, bmi_standard) if bmi is not None else None, "standard": bmi_standard},
        "seven_day_change": seven_day_change,
    }
