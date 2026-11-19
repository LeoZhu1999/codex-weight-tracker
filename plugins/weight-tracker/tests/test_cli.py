import sys
from pathlib import Path

from weight_tracker import cli


def test_chart_command_uses_direct_launcher(monkeypatch):
    called: list[bool] = []
    monkeypatch.setattr(cli, "chart_main", lambda open_browser=True: called.append(open_browser))
    monkeypatch.setattr(sys, "argv", ["weight-tracker", "chart", "--no-browser"])

    cli.main()

    assert called == [False]


def test_chart_command_writes_launcher_log(tmp_path, monkeypatch):
    log_file = tmp_path / "dashboard.log"
    monkeypatch.setattr(cli, "chart_main", lambda open_browser=True: print(f"open_browser={open_browser}"))
    monkeypatch.setattr(sys, "argv", ["weight-tracker", "chart", "--no-browser", "--log-file", str(log_file)])

    cli.main()

    assert log_file.read_text(encoding="utf-8") == "open_browser=False\n"


def test_chart_main_reopens_reused_dashboard_without_waiting(monkeypatch):
    url = "http://127.0.0.1:54321/"
    opened: list[str] = []
    monkeypatch.setattr(cli, "load_config", lambda: object())
    monkeypatch.setattr(cli.DashboardServer, "start_with_ownership", lambda _config: (url, False))
    monkeypatch.setattr(cli.webbrowser, "open_new_tab", lambda value: opened.append(value) or True)
    monkeypatch.setattr(cli.DashboardServer, "wait_for_stop", lambda: (_ for _ in ()).throw(AssertionError("reused service must not wait")))

    cli.chart_main()

    assert opened == [url]


def test_chart_main_opens_and_waits_for_owned_dashboard(monkeypatch):
    url = "http://127.0.0.1:54322/"
    opened: list[str] = []
    waited: list[bool] = []
    monkeypatch.setattr(cli, "load_config", lambda: object())
    monkeypatch.setattr(cli.DashboardServer, "start_with_ownership", lambda _config: (url, True))
    monkeypatch.setattr(cli.webbrowser, "open_new_tab", lambda value: opened.append(value) or True)
    monkeypatch.setattr(cli.DashboardServer, "wait_for_stop", lambda: waited.append(True))

    cli.chart_main()

    assert opened == [url]
    assert waited == [True]


def test_hidden_launcher_prefers_project_python_and_keeps_uv_fallback():
    launcher = Path(__file__).parents[1] / "scripts" / "open-dashboard.vbs"
    source = launcher.read_text(encoding="utf-8")

    assert ".venv\\Scripts\\python.exe" in source
    assert "If fso.FileExists(pythonExe) Then" in source
    assert "uv run --project" in source
    assert "--log-file" in source
    assert "cmd.exe /d /s /c" not in source
    assert "shell.Run command, 0, False" in source
