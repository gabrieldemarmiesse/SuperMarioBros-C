"""Exercise the actual MCP stdio transport against FCEUX; requires a ROM path."""
import asyncio
import json
from pathlib import Path
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    params=StdioServerParameters(command=sys.executable,args=['-m','emulator_use.server'],cwd=str(Path(__file__).resolve().parents[1]))
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write) as client:
            await client.initialize()
            listed=await client.list_tools()
            assert len(listed.tools)==9
            print('MCP tools:',', '.join(t.name for t in listed.tools),flush=True)
            async def call(name,args):
                result=await client.call_tool(name,args)
                assert not result.isError,(name,result)
                if name=='screenshot':
                    assert any(c.type=='image' and c.mimeType=='image/png' for c in result.content)
                    return json.loads(next(c.text for c in result.content if c.type=='text'))
                return result.structuredContent or json.loads(result.content[0].text)
            opened=await call('start_session',{'rom_path':sys.argv[1]})
            sid=opened['session_id']
            args={'session_id':sid}
            try:
                result=await call('step',args|{'frames':120})
                assert result['frame']==120
                shot=await call('screenshot',args)
                assert shot['frame']==120
                await call('save_checkpoint',args|{'name':'baseline'})
                before=await call('read_ram',args)
                await call('step',args|{'frames':1,'buttons':['start']})
                await call('step',args|{'frames':210})
                shot=await call('screenshot',args)
                print('MCP gameplay screenshot:',shot['file'],flush=True)
                await call('load_checkpoint',args|{'name':'baseline'})
                after=await call('read_ram',args)
                assert before['sha256']==after['sha256']
                bad=await client.call_tool('step',args|{'frames':601})
                assert bad.isError
                assert (await call('get_status',args))['frame']==120
            finally:
                await call('close_session',args)
            print('PASS: real MCP stdio, nine tools, image response, input, RAM, checkpoint, invalid request',flush=True)


asyncio.run(main())
