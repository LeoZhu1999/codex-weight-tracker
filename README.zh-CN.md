# Codex Weight Tracker

这是一个本地优先的 Codex 插件：使用 Excel 保存体重记录，通过 MCP 提供新增、查询和两步确认纠错，并在本地浏览器展示每日平均体重、七日滚动平均、七日变化和 BMI。

## Windows 安装

```powershell
git clone https://github.com/LeoZhu1999/codex-weight-tracker.git
cd codex-weight-tracker
.\plugins\weight-tracker\scripts\install.ps1 -WorkbookPath "C:\Users\you\Documents\weight-records.xlsx" -HeightCm 176
```

已有旧版三列中文 Excel（`日期 / 时间 / 体重 (kg)`）时，加上 `-MigrateLegacy`。迁移会先创建带时间戳的备份。

数据不会上传；图表服务仅绑定本机 `127.0.0.1`。BMI 仅用于筛查提示，不构成医疗建议或诊断。
