import asyncio
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from weight_tracker.config import AppConfig, save_config
from weight_tracker.storage import ExcelStorage


def test_mcp_discovers_tools_and_reads_health(tmp_path: Path, monkeypatch):
    config_file = tmp_path / "config.toml"
    monkeypatch.setenv("WEIGHT_TRACKER_CONFIG", str(config_file))
    workbook = tmp_path / "records.xlsx"
    ExcelStorage(workbook).ensure_exists()
    save_config(AppConfig(str(workbook), "Europe/Berlin", 176, "china_adult", "kg", "cm"))

    async def check():
        params = StdioServerParameters(
            command="uv",
            args=["run", "--project", ".", "--frozen", "python", "-m", "weight_tracker.mcp_server"],
        )
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                tools = await session.list_tools()
                names = {tool.name for tool in tools.tools}
                assert {"record_weight", "list_weight_records", "prepare_weight_change", "commit_weight_change", "get_dashboard_url", "health_check"} <= names
                result = await session.call_tool("health_check", {})
                assert "\"status\":\"ok\"" in result.content[0].text.replace(" ", "")

    asyncio.run(check())
