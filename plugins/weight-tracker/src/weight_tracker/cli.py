from __future__ import annotations

import argparse
import json
import webbrowser
from pathlib import Path

from .config import AppConfig, load_config, save_config
from .dashboard import DashboardServer
from .storage import ExcelStorage, migrate_legacy


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="weight-tracker")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--workbook", required=True)
    init.add_argument("--timezone", default="Europe/Berlin")
    init.add_argument("--height-cm", type=float, required=True)
    init.add_argument("--bmi-standard", choices=["china_adult", "who_adult"], default="china_adult")
    init.add_argument("--display-weight-unit", choices=["kg", "lb"], default="kg")
    init.add_argument("--display-height-unit", choices=["cm", "in"], default="cm")
    init.add_argument("--migrate-legacy", action="store_true")
    migrate = sub.add_parser("migrate")
    migrate.add_argument("--source", required=True)
    migrate.add_argument("--timezone", default="Europe/Berlin")
    chart = sub.add_parser("chart", help="Open the local weight dashboard without Codex")
    chart.add_argument("--no-browser", action="store_true", help="Start the dashboard without opening a browser")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    if args.command == "init":
        path = Path(args.workbook).expanduser().resolve()
        if args.migrate_legacy:
            result = migrate_legacy(path, args.timezone)
        else:
            ExcelStorage(path).ensure_exists()
            result = {"workbook": str(path)}
        config = AppConfig(str(path), args.timezone, args.height_cm, args.bmi_standard, args.display_weight_unit, args.display_height_unit)
        config_file = save_config(config)
        result["config"] = str(config_file)
        print(json.dumps(result, ensure_ascii=False))
        return
    if args.command == "migrate":
        result = migrate_legacy(Path(args.source).expanduser().resolve(), args.timezone)
        print(json.dumps(result, ensure_ascii=False))
        return
    chart_main(open_browser=not args.no_browser)


def chart_main(open_browser: bool = True) -> None:
    url, owns_server = DashboardServer.start_with_ownership(load_config())
    if open_browser:
        webbrowser.open(url)
    print(f"Dashboard running at {url}. Keep this window open while viewing it.", flush=True)
    if owns_server:
        try:
            DashboardServer.wait_for_stop()
        except KeyboardInterrupt:
            return


if __name__ == "__main__":
    main()
