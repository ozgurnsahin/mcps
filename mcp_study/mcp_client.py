from contextlib import AsyncExitStack
from typing import Dict, List
from dotenv import load_dotenv

from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPClient:
    def __init__(self):
        load_dotenv()
        self.sessions: Dict[str, ClientSession] = {}
        self.exit_stack = AsyncExitStack()
        self.client = OpenAI()

    async def connect_to_servers(self):
        time_server_params = StdioServerParameters(
            command="uvx",
            args=["mcp-server-time"],
            env=None
        )
        
        stdio_transport_time = await self.exit_stack.enter_async_context(stdio_client(time_server_params))
        stdio_time, write_time = stdio_transport_time
        session_time = await self.exit_stack.enter_async_context(ClientSession(stdio_time, write_time))
        await session_time.initialize()
        self.sessions["time"] = session_time
        
        browser_server_params = StdioServerParameters(
            command="python",
            args=["mcp_server.py"],
            env=None
        )
        
        stdio_transport_browser = await self.exit_stack.enter_async_context(stdio_client(browser_server_params))
        stdio_browser, write_browser = stdio_transport_browser
        session_browser = await self.exit_stack.enter_async_context(ClientSession(stdio_browser, write_browser))
        await session_browser.initialize()
        self.sessions["browser"] = session_browser
        
        await self.list_all_tools()
    
    async def list_all_tools(self):
        all_tools = []
        for server_name, session in self.sessions.items():
            response = await session.list_tools()
            tools = response.tools
            print(f"\n{server_name.title()} server tools:", [tool.name for tool in tools])
            all_tools.extend(tools)
        return all_tools
        
    async def process_query(self, query: str):
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]
        
        all_tools = await self.list_all_tools()
        tool_list = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        } for tool in all_tools]
        
        response = self.client.chat.completions.create(
            model = "gpt-4o-mini",
            tools=tool_list,
            max_tokens=1000,
            messages=messages
        )
        
        final_text = []
        
        message = response.choices[0].message
        
        if message.content:
            final_text.append(message.content)
        
        if message.tool_calls:
            tool_messages = []
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = eval(tool_call.function.arguments)

                target_session = None
                for session in self.sessions.values():
                    response = await session.list_tools()
                    if any(tool.name == tool_name for tool in response.tools):
                        target_session = session
                        break
                
                if target_session:
                    result = await target_session.call_tool(tool_name, tool_args)
                    final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")
                    
                    tool_messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "content": str(result.content)
                    })
                else:
                    tool_messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "content": f"Error: Tool {tool_name} not found in any server"
                    })
            
            messages.append({
                "role": "assistant",
                "tool_calls": message.tool_calls
            })
            
            messages.extend(tool_messages)
            
            final_response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=1000,
                messages=messages,
                tools=tool_list
            )
            
            if final_response.choices[0].message.content:
                final_text.append(final_response.choices[0].message.content)

        return "\n".join(final_text)
    
    async def chat(self):
        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == 'quit':
                    break

                response = await self.process_query(query)
                print("\n" + response)
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    async def cleanup(self):
        await self.exit_stack.aclose()
                

            
        
        
        
        
    
    