from mcp.server.fastmcp import FastMCP
import httpx
import os
from typing import Dict, Any
import json

mcp = FastMCP("browser")
serper_api_key = os.getenv("SERPER_API_KEY")
search_url = "https://google.serper.dev/search"

async def send_request(url: str) -> Dict[str, Any]:
    headers = {
        "X-API-KEY" : serper_api_key,
        "content-type" : "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error: {str(e)}")
            return None

@mcp.tool()
async def search_web_tool(url: str) -> Dict[str, Any]:
    try:
        data = await send_request(url)
        
        if not data:
            return "Unable to fetch alerts or no alerts found."

        text = json.dumps(data,indent=2)
        
        return text
    except Exception as e:
        print(f"Error: {str(e)}")
        return None
    
if __name__ == "__main__":
    mcp.run()