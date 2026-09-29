"""Protocol smoke test; no emulator or ROM is required."""
import asyncio
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_stdio_discovery_and_unknown_session():
    async def exercise():
        params = StdioServerParameters(
            command=sys.executable,
            args=['-m', 'emulator_use.server'],
            cwd=str(Path(__file__).resolve().parents[1]),
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                result = await client.list_tools()
                assert {tool.name for tool in result.tools} == {
                    'start_session', 'load_movie', 'get_status', 'step', 'screenshot', 'read_ram',
                    'save_checkpoint', 'load_checkpoint', 'watch_writes', 'close_session',
                }
                error = await client.call_tool('get_status', {'session_id': 'missing'})
                assert error.isError
                closed = await client.call_tool('close_session', {'session_id': 'missing'})
                assert not closed.isError
    asyncio.run(exercise())
