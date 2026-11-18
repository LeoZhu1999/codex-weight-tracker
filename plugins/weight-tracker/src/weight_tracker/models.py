from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WeightUnit(str, Enum):
    KG = "kg"
    LB = "lb"


class TimeSource(str, Enum):
    USER_PROVIDED = "user_provided"
    MESSAGE_TIME = "message_time"
    LEGACY_IMPORT = "legacy_import"


class WeightInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    measured_at: datetime
    timezone: str = Field(min_length=1, max_length=64)
    weight_value: float = Field(gt=20, lt=500)
    weight_unit: WeightUnit
    time_source: TimeSource
    note: str | None = Field(default=None, max_length=500)
    request_id: str = Field(min_length=8, max_length=128)
    allow_duplicate: bool = False

    @field_validator("measured_at")
    @classmethod
    def timestamp_needs_offset(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("measured_at must include a UTC offset")
        return value

    @property
    def weight_kg(self) -> float:
        return round(self.weight_value if self.weight_unit is WeightUnit.KG else self.weight_value * 0.45359237, 3)


class StoredRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    request_id: str
    measured_at: datetime
    timezone: str
    weight_kg: float
    time_source: TimeSource
    note: str | None = None
    created_at: datetime | None = None

    @classmethod
    def from_input(cls, item: WeightInput) -> "StoredRecord":
        return cls(
            record_id=f"wr_{uuid4().hex}",
            request_id=item.request_id,
            measured_at=item.measured_at,
            timezone=item.timezone,
            weight_kg=item.weight_kg,
            time_source=item.time_source,
            note=item.note,
            created_at=datetime.now(item.measured_at.tzinfo),
        )


class ChangeAction(str, Enum):
    UPDATE = "update"
    DELETE = "delete"


class ChangePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    measured_at: datetime | None = None
    timezone: str | None = None
    weight_value: float | None = Field(default=None, gt=20, lt=500)
    weight_unit: WeightUnit | None = None
    note: str | None = Field(default=None, max_length=500)

    @field_validator("measured_at")
    @classmethod
    def changed_timestamp_needs_offset(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("measured_at must include a UTC offset")
        return value


class PendingChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str
    action: ChangeAction
    record_id: str
    patch: ChangePatch | None
    expires_at: datetime
