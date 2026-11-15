# 에이전트(클라이언트)가 서버에 연결하기
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
server = StdioServerParameters(command='python', args=['weather_mcp_server.py'])
async def main():
	async with stdio_client(server) as (read, write):
		await session.initialize()
		# 1. 서버가 제공하는 툴 목록을 자동으로 받아온다
		tools = await session.list_tools()
		print([t.name for t in tools.tools])    # ['get_weather']
		# 2. 이름과 인자만 넘겨 툴을 호출한다.
		result = await session.call_tool('get_weather', {'city': 'Seoul'})
		print(result.content[0].text)
asyncio.run(main())