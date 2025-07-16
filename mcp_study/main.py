import sys
import asyncio 

from mcp_client import MCPClient

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server()
        await client.chat()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
