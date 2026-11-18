from datetime import datetime
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")

from weight_tracker.config import AppConfig
from weight_tracker.dashboard import DashboardServer
from weight_tracker.models import TimeSource, WeightInput
from weight_tracker.storage import ExcelStorage


def _browser_path() -> Path | None:
    for value in (
        r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        r"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    ):
        path = Path(value)
        if path.exists():
            return path
    return None


@pytest.mark.skipif(_browser_path() is None, reason="Chrome or Edge is required for browser dashboard verification")
def test_dashboard_browser_uses_real_time_spacing_and_fits_viewport(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("WEIGHT_TRACKER_DATA_DIR", str(tmp_path / "runtime"))
    workbook = tmp_path / "records.xlsx"
    storage = ExcelStorage(workbook)
    for index, (day, weight) in enumerate(((1, 84.0), (2, 83.8), (9, 83.4))):
        storage.append(WeightInput(measured_at=datetime(2026, 1, day, 8, tzinfo=datetime.now().astimezone().tzinfo), timezone="Europe/Berlin", weight_value=weight, weight_unit="kg", time_source=TimeSource.USER_PROVIDED, request_id=f"browser-{index}"))
    server = DashboardServer(AppConfig(str(workbook)), idle_seconds=30)
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(executable_path=str(_browser_path()), headless=True)
            page = browser.new_page(viewport={"width": 1366, "height": 768})
            page.goto(server.url)
            page.wait_for_function("document.querySelector('#latest').textContent !== '—'")
            assert page.locator("#bmi-scale").inner_text().split() == ["18.5", "24", "28"]
            visibility = page.evaluate("""() => {
                const chart = echarts.getInstanceByDom(document.querySelector('#chart'));
                return chart.getOption().series.map(series => series.data.length);
            }""")
            assert visibility[0] == 3
            assert visibility[1] == 0
            for width, height in ((1920, 1080), (1366, 768), (1024, 600), (360, 640)):
                page.set_viewport_size({"width": width, "height": height})
                assert page.evaluate("document.documentElement.scrollHeight <= window.innerHeight")
                assert page.locator("#chart").bounding_box()["height"] > 100
            coordinates = page.evaluate("""() => {
                const chart = echarts.getInstanceByDom(document.querySelector('#chart'));
                return ['2026-01-01','2026-01-02','2026-01-09'].map(date => chart.convertToPixel({xAxisIndex: 0}, new Date(date + 'T12:00:00').getTime()));
            }""")
            assert (coordinates[2] - coordinates[1]) / (coordinates[1] - coordinates[0]) == pytest.approx(7, rel=.2)
            page.get_by_role("button", name="Switch language").click()
            assert page.get_by_role("button", name="30D").is_visible()
            page.get_by_role("button", name="7D").click()
            page.get_by_role("button", name="7-day rolling average").click()
            assert page.locator("button[data-series='average']").get_attribute("aria-pressed") == "true"
            page.reload()
            page.wait_for_function("document.querySelector('#latest').textContent !== '—'")
            assert page.locator("button[data-range='7']").evaluate("element => element.classList.contains('active')")
            assert page.locator("button[data-series='average']").get_attribute("aria-pressed") == "true"
            assert page.locator("#chart").is_visible()
            browser.close()
    finally:
        server.stop()
