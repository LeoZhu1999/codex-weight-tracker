[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$WorkbookPath,
  [Parameter(Mandatory = $true)][double]$HeightCm,
  [string]$Timezone = "Europe/Berlin",
  [ValidateSet("china_adult", "who_adult")][string]$BmiStandard = "china_adult",
  [ValidateSet("kg", "lb")][string]$DisplayWeightUnit = "kg",
  [switch]$MigrateLegacy,
  [switch]$LocalMarketplace
)

$ErrorActionPreference = "Stop"
$pluginRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
foreach ($tool in @("uv", "codex")) {
  if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
    throw "Missing required command: $tool"
  }
}

$initArgs = @("run", "--project", $pluginRoot, "--frozen", "python", "-m", "weight_tracker.cli", "init", "--workbook", $WorkbookPath, "--height-cm", $HeightCm, "--timezone", $Timezone, "--bmi-standard", $BmiStandard, "--display-weight-unit", $DisplayWeightUnit)
if ($MigrateLegacy) { $initArgs += "--migrate-legacy" }
& uv @initArgs
if ($LASTEXITCODE -ne 0) { throw "Initialization failed." }

if ($LocalMarketplace) {
  $marketplaceRoot = Resolve-Path (Join-Path $pluginRoot "..\..")
  & codex plugin marketplace add $marketplaceRoot
} else {
  & codex plugin marketplace add "LeoZhu1999/codex-weight-tracker" --ref main
}
if ($LASTEXITCODE -ne 0) { throw "Marketplace registration failed." }
& codex plugin add "weight-tracker@codex-weight-tracker"
if ($LASTEXITCODE -ne 0) { throw "Plugin installation failed." }

Write-Host "Codex Weight Tracker is installed. Start a new Codex task to load its Skill and MCP tools." -ForegroundColor Green
Write-Host "To open the dashboard without Codex, double-click: $pluginRoot\scripts\open-dashboard.cmd" -ForegroundColor Cyan
