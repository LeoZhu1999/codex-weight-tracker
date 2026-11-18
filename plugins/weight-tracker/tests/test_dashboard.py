import json
from pathlib import Path
from urllib.request import Request, urlopen

from weight_tracker.config import AppConfig
from weight_tracker.dashboard import DashboardServer
from weight_tracker.storage import ExcelStorage


def _request(url: str, method: str = "GET", token: str | None = None):
    headers = {"X-Weight-Tracker-Token": token} if token else {}
    return urlopen(Request(url, method=method, headers=headers), timeout=3)


def test_dashboard_serves_static_assets_and_stops(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("WEIGHT_TRACKER_DATA_DIR", str(tmp_path / "runtime"))
    workbook = tmp_path / "records.xlsx"
    ExcelStorage(workbook).ensure_exists()
    server = DashboardServer(AppConfig(str(workbook)), idle_seconds=30)
    try:
        with _request(server.url) as response:
            body = response.read().decode("utf-8")
            assert response.status == 200
            assert "__DASHBOARD_TOKEN__" not in body
            assert "echarts.min.js" in body
        with _request(server.url + "assets/dashboard.js") as response:
            assert response.status == 200
            assert b"type:'time'" in response.read()
        with _request(server.url + "assets/vendor/echarts.min.js") as response:
            assert response.status == 200
            assert len(response.read()) > 1_000_000
        state = json.loads((tmp_path / "runtime" / "dashboard-state.json").read_text(encoding="utf-8"))
        with _request(server.url + "api/heartbeat", "POST", state["token"]) as response:
            assert response.status == 204
        with _request(server.url + "api/shutdown", "POST", state["token"]) as response:
            assert response.status == 204
        server.wait()
        assert not (tmp_path / "runtime" / "dashboard-state.json").exists()
    finally:
        server.stop()


def test_dashboard_idle_timeout_and_reuse(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("WEIGHT_TRACKER_DATA_DIR", str(tmp_path / "runtime"))
    workbook = tmp_path / "records.xlsx"
    ExcelStorage(workbook).ensure_exists()
    server = DashboardServer(AppConfig(str(workbook)), idle_seconds=1)
    try:
        server.wait()
        assert server.stopped.is_set()
    finally:
        server.stop()
