from __future__ import annotations

import os
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

from platformdirs import user_data_dir


APP_NAME = "CodexWeightTracker"


@dataclass
class AppConfig:
    workbook_path: str
    timezone: str = "Europe/Berlin"
    height_cm: float = 176.0
    bmi_standard: str = "china_adult"
    display_weight_unit: str = "kg"
    display_height_unit: str = "cm"

    @property
    def data_dir(self) -> Path:
        return Path(self.workbook_path).expanduser().resolve().parent


def default_data_dir() -> Path:
    configured = os.environ.get("WEIGHT_TRACKER_DATA_DIR")
    return Path(configured).expanduser() if configured else Path(user_data_dir(APP_NAME, appauthor=False))


def config_path() -> Path:
    configured = os.environ.get("WEIGHT_TRACKER_CONFIG")
    return Path(configured).expanduser() if configured else default_data_dir() / "config.toml"


def load_config() -> AppConfig:
    path = config_path()
    if not path.exists():
        raise FileNotFoundError(f"Weight Tracker is not initialized. Run `weight-tracker init`. Expected config: {path}")
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    return AppConfig(**raw["tracker"])


def save_config(config: AppConfig) -> Path:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(config)
    lines = ["[tracker]"] + [f'{key} = {value!r}' for key, value in data.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
