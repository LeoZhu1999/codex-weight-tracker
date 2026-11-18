# Codex Weight Tracker

这是一个本地优先的 Codex 插件：使用 Excel 保存体重记录，通过 MCP 提供新增、查询和两步确认纠错，并在本地浏览器展示每日平均体重、七日滚动平均、七日变化和 BMI。

## Windows 安装

```powershell
git clone https://github.com/LeoZhu1999/codex-weight-tracker.git
cd codex-weight-tracker
.\plugins\weight-tracker\scripts\install.ps1 -WorkbookPath "C:\Users\you\Documents\weight-records.xlsx" -HeightCm 176
```

已有旧版三列中文 Excel（`日期 / 时间 / 体重 (kg)`）时，加上 `-MigrateLegacy`。迁移会先创建带时间戳的备份。

## 不通过 Codex 打开趋势图

运行安装脚本后，在克隆下来的仓库中双击 `plugins\weight-tracker\scripts\打开体重趋势图.lnk`。它使用随插件提供的体脂秤趋势图标，直接用默认浏览器打开本地仪表板，不显示命令行窗口；最后一个仪表板页面关闭约两分钟后，本地服务会自动退出。该启动器直接读取本地配置中的工作簿路径，不需要打开 Codex；`open-dashboard.vbs` 仍保留为可移植的备用启动器。

仪表板按真实日期间隔显示测量点，支持时间区间、平移缩放、十字光标、实心曲线开关、PNG 导出和中英语言切换。标题与指标卡合并为紧凑信息区，让图表获得更多空间。首次默认只显示日均体重，并显示 BMI 分段阈值与当前位置；关闭页面后会保留语言、时间区间、缩放和曲线显示设置。Apache ECharts 已随插件本地打包，打开图表不依赖网络。

数据不会上传；图表服务仅绑定本机 `127.0.0.1`。BMI 仅用于筛查提示，不构成医疗建议或诊断。
