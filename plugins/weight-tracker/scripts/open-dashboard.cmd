@echo off
setlocal

where uv >nul 2>nul
if errorlevel 1 (
  echo The required command 'uv' was not found. Re-run the plugin installer or install uv first.
  pause
  exit /b 1
)

uv run --project "%~dp0.." --frozen python -m weight_tracker.cli chart
if errorlevel 1 pause
