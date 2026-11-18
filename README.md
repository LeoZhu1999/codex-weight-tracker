# Codex Weight Tracker

Local-first Codex plugin for body-weight logging. It stores records in an Excel workbook, exposes typed MCP tools, and opens a local browser dashboard with daily averages, 7-day trend changes, and BMI.

## Install on Windows

```powershell
git clone https://github.com/LeoZhu1999/codex-weight-tracker.git
cd codex-weight-tracker
.\plugins\weight-tracker\scripts\install.ps1 -WorkbookPath "C:\Users\you\Documents\weight-records.xlsx" -HeightCm 176
```

Use `-MigrateLegacy` when the workbook is the legacy three-column Chinese `日期 / 时间 / 体重 (kg)` file. The installer creates a timestamped backup before migration.

The installer registers the Git marketplace, installs `weight-tracker`, initializes local configuration, and checks the workbook. Restart Codex or start a new task after installation.

## Open the dashboard without Codex

Double-click `plugins\weight-tracker\scripts\open-dashboard.cmd` in the cloned repository. It opens the local dashboard in your default browser and keeps a small command window running while the dashboard is open. Your local configuration identifies the workbook; no Codex session is needed.

## Privacy and safety

- Data remains on the local computer. The MCP service uses STDIO and the dashboard binds only to `127.0.0.1`.
- The repository does not contain personal workbooks or configuration.
- BMI is a screening metric, not medical advice or diagnosis.

## Development

```powershell
cd plugins\weight-tracker
uv sync --all-extras
uv run pytest
uv run python -m weight_tracker.mcp_server
uv run python -m weight_tracker.cli chart
```

The source repository is also a Codex marketplace. For a local development install, use:

```powershell
codex plugin marketplace add .\
codex plugin add weight-tracker@codex-weight-tracker
```
