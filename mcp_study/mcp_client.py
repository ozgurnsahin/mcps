from contextlib import AsyncExitStack
from typing import Optional
from dotenv import load_dotenv

from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPClient:
    def __init__(self):
        load_dotenv()
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.client = OpenAI()

    async def connect_to_server(self):
        server_params = StdioServerParameters(
            command="uvx",
            args = ["mcp-server-time"],
            env=None
        )
        
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        
        await self.session.initialize()
        
        # Get tools list
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])
        
    async def process_query(self, query: str):
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]
        
        response = await self.session.list_tools()
        tool_list = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        } for tool in response.tools]
        
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
                
                result = await self.session.call_tool(tool_name, tool_args)
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")
                
                tool_messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "content": str(result.content)
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
                

            
        
        
        
        
    
    