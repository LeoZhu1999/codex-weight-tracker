import sys

from weight_tracker import cli


def test_chart_command_uses_direct_launcher(monkeypatch):
    called: list[bool] = []
    monkeypatch.setattr(cli, "chart_main", lambda open_browser=True: called.append(open_browser))
    monkeypatch.setattr(sys, "argv", ["weight-tracker", "chart", "--no-browser"])

    cli.main()

    assert called == [False]
