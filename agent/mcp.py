# Credit: https://github.com/langchain-ai/langchain-mcp-adapters/

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Callable, Awaitable
from contextlib import AsyncExitStack
from mcp.client.streamable_http import streamablehttp_client, SessionMessage
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from mcp.types import Tool, CallToolResult, ImageContent, TextContent, EmbeddedResource

NonTextContent = ImageContent | EmbeddedResource
MAX_ITERATIONS = 1000


@dataclass
class ServerInfo:
    connection_exit_stack: AsyncExitStack
    read_stream: MemoryObjectReceiveStream[SessionMessage | Exception]
    write_stream: MemoryObjectSendStream[SessionMessage]
    server_config: Dict[str, Any]
    errors: Optional[List[str]] = None


@dataclass
class SessionInfo:
    sessions: List[ClientSession]
    exit_stacks: Dict[str, AsyncExitStack]


@dataclass
class McpTool:
    name: str
    description: Optional[str]
    input_schema: Optional[Dict[str, Any]]
    annotations: Optional[Dict[str, Any]]
    handler: Callable[..., Awaitable[Any]]


class MCPClient:
    def __init__(self) -> None:
        self.servers: Dict[str, ServerInfo] = {}
        self.sessions: Dict[str, SessionInfo] = {}  # session_id -> SessionInfo
        self._session_counter: int = 0

    async def start_session(
        self,
    ) -> tuple[str, List[Dict[str, Any]], Dict[str, Callable[..., Awaitable[Any]]]]:
        """Start a new session for all servers and return session_id, tools, and handlers"""
        self._session_counter += 1
        session_id = f"session_{self._session_counter}"

        # Collect all tools and handlers from all servers
        all_tools: List[Dict[str, Any]] = []
        all_handlers: Dict[str, Callable[..., Awaitable[Any]]] = {}

        # Create sessions for all servers
        self.sessions[session_id] = session_info = SessionInfo(
            sessions=[],
            exit_stacks={},
        )
        for name, server_info in self.servers.items():
            # Create session exit stack for this specific session
            session_info.exit_stacks[name] = session_exit_stack = AsyncExitStack()

            # Skip servers with errors
            if server_info.errors:
                continue

            # Create and initialize session using existing connection
            session = await session_exit_stack.enter_async_context(
                ClientSession(server_info.read_stream, server_info.write_stream)
            )
            await session.initialize()

            # Load tools for this server
            mcp_tools: List[McpTool] = await load_mcp_tools(session)

            # Collect tools and handlers
            server_tools = self._get_tools_for_session(mcp_tools)
            server_handlers = self._get_handlers_for_session(mcp_tools)

            all_tools.extend(server_tools)
            all_handlers.update(server_handlers)

            session_info.sessions.append(session)

        return session_id, all_tools, all_handlers

    async def end_session(self, session_id: str) -> None:
        """End a specific session"""
        if session_id in self.sessions:
            server_info = self.sessions[session_id]

            # Close session
            # await server_info.exit_stack.aclose()
            for exit_stack in server_info.exit_stacks.values():
                await exit_stack.aclose()
            del self.sessions[session_id]

    async def _add_http_server(self, server_name: str, server_url: str) -> None:
        """Add a new HTTP MCP server"""
        if server_url in self.servers:
            await self._remove_server(server_url)

        try:
            # Create an exit stack to manage this server's connection lifecycle
            exit_stack = AsyncExitStack()

            # Connect to HTTP server
            read_stream, write_stream, _ = await exit_stack.enter_async_context(
                streamablehttp_client(server_url)
            )

            # Store session info and tools with connection information
            self.servers[server_name] = ServerInfo(
                connection_exit_stack=exit_stack,
                read_stream=read_stream,
                write_stream=write_stream,
                server_config={"url": server_url},
            )
        except Exception as e:
            # Clean up on error
            if "exit_stack" in locals():
                await exit_stack.aclose()
            raise RuntimeError(f"Failed to connect to HTTP server {server_url}") from e

    async def _add_stdio_server(
        self,
        server_name: str,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> None:
        """Add a new stdio MCP server"""
        if server_name in self.servers:
            await self._remove_server(server_name)

        try:
            # Create an exit stack to manage this server's connection lifecycle
            exit_stack = AsyncExitStack()

            # Connect to stdio server
            read_stream, write_stream = await exit_stack.enter_async_context(
                stdio_client(
                    StdioServerParameters(
                        command=command,
                        args=args or [],
                        env=env,
                    )
                )
            )

            # Store session info and tools with connection information
            self.servers[server_name] = ServerInfo(
                connection_exit_stack=exit_stack,
                read_stream=read_stream,
                write_stream=write_stream,
                server_config={"command": command, "args": args, "env": env},
            )
        except Exception as e:
            # Clean up on error
            if "exit_stack" in locals():
                await exit_stack.aclose()
            raise RuntimeError(
                f"Failed to connect to stdio server {server_name}: {e}"
            ) from e

    def _config_matches(
        self, server_info: ServerInfo, new_config: Dict[str, Any]
    ) -> bool:
        """Check if server configuration matches the new config"""

        # Don't reuse connections with errors
        if server_info.errors:
            return False

        current_config = server_info.server_config

        # Compare key fields
        if "command" in new_config:
            return (
                current_config.get("command") == new_config["command"]
                and current_config.get("args") == new_config.get("args")
                and current_config.get("env") == new_config.get("env")
            )
        elif "url" in new_config:
            return current_config.get("url") == new_config["url"]

        return False

    async def sync_config(self, config: Dict[str, Any]) -> None:
        """Sync servers from Claude's MCP configuration format

        Expected format:
        {
            "mcpServers": {
                "server_name": {
                    "command": "path/to/executable",
                    "args": ["arg1", "arg2"],
                    "env": {"VAR": "value"}
                }
            }
        }
        """
        mcp_servers = config.get("mcpServers", {})

        # Track which servers should remain
        servers_to_keep = set()
        for server_name, server_config in mcp_servers.items():
            # Check if server already exists with same config
            if server_name in self.servers and self._config_matches(
                self.servers[server_name], server_config
            ):
                servers_to_keep.add(server_name)

        # Remove servers that are out-dated
        servers_to_remove = set(self.servers.keys()) - servers_to_keep
        for server_name in servers_to_remove:
            await self._remove_server(server_name)

        # Check existing servers and add new ones
        for server_name, server_config in mcp_servers.items():
            if server_name in servers_to_keep:
                # Server already exists with same config, skip
                continue

            # Add or update server
            if "command" in server_config:
                # Stdio server
                await self._add_stdio_server(
                    server_name=server_name,
                    command=server_config["command"],
                    args=server_config.get("args"),
                    env=server_config.get("env"),
                )
            elif "url" in server_config:
                # HTTP server
                await self._add_http_server(
                    server_name=server_name,
                    server_url=server_config["url"],
                )
            else:
                raise ValueError(
                    f"Invalid server configuration for {server_name}: missing 'command' or 'url'"
                )

    async def _remove_server(self, server_url: str) -> None:
        """Remove an MCP server"""
        if server_url in self.servers:
            for session_info in self.sessions.values():
                # Remove this server from all sessions
                if server_url in session_info.exit_stacks:
                    await session_info.exit_stacks[server_url].aclose()
                    del session_info.exit_stacks[server_url]

            server_info = self.servers[server_url]
            # Properly close the connection
            await server_info.connection_exit_stack.aclose()
            del self.servers[server_url]

    async def _close_all_servers(self) -> None:
        """Close all server connections"""
        for session_id in list(self.sessions.keys()):
            await self.end_session(session_id)
        for server_url in list(self.servers.keys()):
            await self._remove_server(server_url)

    def _get_tools_for_session(self, mcp_tools: List[McpTool]) -> List[Dict[str, Any]]:
        """Private method to get tools for a specific session"""
        tools: List[Dict[str, Any]] = []
        for tool in mcp_tools:
            tool_dict: Dict[str, Any] = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.input_schema or {},
                },
            }
            tools.append(tool_dict)
        return tools

    def _get_handlers_for_session(
        self, mcp_tools: List[McpTool]
    ) -> Dict[str, Callable[..., Awaitable[Any]]]:
        """Private method to get handlers for a specific session"""
        return {tool.name: tool.handler for tool in mcp_tools}

    def get_status(self) -> Dict[str, Any]:
        """Get status of all servers

        Returns:
            Dict mapping server names to either True (healthy) or list of errors
        """
        status = {}
        for server_name, server_info in self.servers.items():
            if server_info.errors:
                status[server_name] = server_info.errors
            else:
                status[server_name] = True
        return status

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._close_all_servers()


async def _list_all_tools(session: ClientSession) -> List[Tool]:
    current_cursor: str | None = None
    all_tools: list[Tool] = []

    iterations = 0

    while True:
        iterations += 1
        if iterations > MAX_ITERATIONS:
            raise RuntimeError("Reached max of 1000 iterations while listing tools.")

        list_tools_page_result = await session.list_tools(cursor=current_cursor)

        if list_tools_page_result.tools:
            all_tools.extend(list_tools_page_result.tools)

        if list_tools_page_result.nextCursor is None:
            break

        current_cursor = list_tools_page_result.nextCursor
    return all_tools


def _convert_call_tool_result(
    call_tool_result: CallToolResult,
) -> tuple[str | List[str], Optional[List[NonTextContent]]]:
    text_contents: List[TextContent] = []
    non_text_contents: List[NonTextContent] = []
    for content in call_tool_result.content:
        if isinstance(content, TextContent):
            text_contents.append(content)
        else:
            non_text_contents.append(content)

    tool_content: str | List[str] = [content.text for content in text_contents]
    if not text_contents:
        tool_content = ""
    elif len(text_contents) == 1:
        tool_content = tool_content[0]

    if call_tool_result.isError:
        raise RuntimeError(tool_content)

    return tool_content, non_text_contents or None


def convert_mcp_tool(
    session: ClientSession,
    tool: Tool,
) -> McpTool:
    async def call_tool(
        **params: Dict[str, Any],
    ) -> tuple[str | List[str], Optional[List[NonTextContent]]]:
        call_tool_result = await session.call_tool(tool.name, params)
        return _convert_call_tool_result(call_tool_result)

    return McpTool(
        name=tool.name,
        description=tool.description or "",
        input_schema=tool.inputSchema,
        annotations=tool.annotations.model_dump() if tool.annotations else None,
        handler=call_tool,
    )


async def load_mcp_tools(
    session: ClientSession,
) -> List[McpTool]:
    tools = await _list_all_tools(session)
    converted_tools = [convert_mcp_tool(session, tool) for tool in tools]
    return converted_tools
