# Credit: https://github.com/langchain-ai/langchain-mcp-adapters/

import json
import os
import asyncio
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Awaitable
import copy

from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from mcp import ClientSession, StdioServerParameters
from mcp.client.streamable_http import streamablehttp_client, SessionMessage
from mcp.client.stdio import stdio_client
from mcp.types import (
    Tool,
    CallToolResult,
    ImageContent,
    TextContent,
    EmbeddedResource,
    AudioContent,
    ResourceLink,
)
from utils.logger import IOSYSLogger

NonTextContent = ImageContent | AudioContent | ResourceLink | EmbeddedResource
MAX_ITERATIONS = 1000

logger = IOSYSLogger("MCP")


@dataclass
class ServerInfo:
    connection_exit_stack: AsyncExitStack
    read_stream: MemoryObjectReceiveStream[SessionMessage | Exception]
    write_stream: MemoryObjectSendStream[SessionMessage]
    server_config: Dict[str, Any]
    errors: List[str] = field(default_factory=list)


@dataclass
class SessionInfo:
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
        self.config_file_path = os.environ.get(
            "MCP_CONFIG_FILE", "./data/mcp_config.json"
        )
        self._shutdown_lock = asyncio.Lock()
        self._load_config_from_file()

        # Remove the automatic delayed sync - let it be called manually when needed

    async def ensure_initialized(self) -> None:
        """Ensure the client is initialized with config. Call this manually when needed."""
        try:
            config = self._load_config_from_file()
            if config:
                await self.sync_config(config)
                logger.info("Initialization sync completed successfully")
        except Exception as e:
            logger.error(f"Error during initialization sync: {e}")

    def _load_config_from_file(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if not self.config_file_path or not os.path.exists(self.config_file_path):
            return {}

        try:
            with open(self.config_file_path, "r", encoding="utf-8") as f:
                d = json.load(f)
                logger.info(
                    f"Loaded MCP config from {self.config_file_path} with {len(d.get('mcpServers', {}))} servers"
                )
                return d
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading MCP config from {self.config_file_path}: {e}")
            return {}

    def _save_config_to_file(self, config: Dict[str, Any]) -> None:
        """Save configuration to file"""
        if not self.config_file_path:
            return

        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_file_path), exist_ok=True)

            with open(self.config_file_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving MCP config to {self.config_file_path}: {e}")
            raise

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return self._load_config_from_file()

    async def start_session(
        self,
    ) -> tuple[str, List[Dict[str, Any]], Dict[str, Callable[..., Awaitable[Any]]]]:
        """Start a new session for all servers and return session_id, tools, and handlers"""
        self._session_counter += 1
        session_id = f"session_{self._session_counter}"
        logger.info(f"Starting session {session_id}")

        # Collect all tools and handlers from all servers
        all_tools: List[Dict[str, Any]] = []
        all_handlers: Dict[str, Callable[..., Awaitable[Any]]] = {}

        # Create sessions for all servers
        self.sessions[session_id] = session_info = SessionInfo(
            exit_stacks={},
        )
        for name, server_info in self.servers.items():
            try:
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
                logger.debug(f"Loaded {len(mcp_tools)} tools from server {name}")

                # Collect tools and handlers
                server_tools = self._get_tools_for_session(mcp_tools)
                server_handlers = self._get_handlers_for_session(mcp_tools)

                all_tools.extend(server_tools)
                all_handlers.update(server_handlers)
            except Exception as e:
                logger.error(f"Failed to start session for server {name}: {e}")
                server_info.errors.append(str(e))
                # Clean up the exit stack if it was created with better error handling
                if name in session_info.exit_stacks:
                    try:
                        await session_info.exit_stacks[name].aclose()
                    except Exception as cleanup_error:
                        logger.warning(
                            f"Error during session exit stack cleanup for {name}: {cleanup_error}"
                        )
                    finally:
                        del session_info.exit_stacks[name]

        logger.info(
            f"Session {session_id} started with {len(all_tools)} tools from {len([s for s in self.servers.values() if not s.errors])} servers"
        )
        return session_id, all_tools, all_handlers

    async def end_session(self, session_id: str) -> None:
        """End a specific session"""
        if session_id in self.sessions:
            logger.info(f"Ending session {session_id}")
            session_info = self.sessions[session_id]

            # Close session exit stacks with proper error handling
            exit_stacks_to_close = list(session_info.exit_stacks.items())
            for name, exit_stack in exit_stacks_to_close:
                try:
                    # Direct cleanup with cancel scope error handling
                    await self._cleanup_session_exit_stack(name, exit_stack)
                    if name in session_info.exit_stacks:
                        del session_info.exit_stacks[name]
                except Exception as e:
                    logger.error(f"Error closing session for {name}: {e}")
                    if name in self.servers:
                        self.servers[name].errors.append(f"Session cleanup error: {e}")
                    # Always remove from dict even if cleanup failed
                    if name in session_info.exit_stacks:
                        del session_info.exit_stacks[name]

            del self.sessions[session_id]
            logger.debug(f"Session {session_id} ended")

    async def _cleanup_session_exit_stack(
        self, name: str, exit_stack: AsyncExitStack
    ) -> None:
        """Helper method to clean up a session exit stack"""
        try:
            await exit_stack.aclose()
        except Exception as e:
            # Handle cancel scope errors more gracefully
            error_msg = str(e)
            if "cancel scope" in error_msg.lower():
                logger.debug(f"Cancel scope conflict during cleanup for {name}: {e}")
                # Don't re-raise cancel scope errors as they're expected during shutdown
            else:
                logger.warning(f"Error during exit stack cleanup for {name}: {e}")
                raise

    async def _add_http_server(self, server_name: str, server_url: str) -> None:
        """Add a new HTTP MCP server"""
        logger.info(f"Adding HTTP server: {server_name} ({server_url})")
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
            logger.info(f"HTTP server {server_name} added successfully")
        except Exception as e:
            logger.error(f"Failed to add HTTP server {server_name}: {e}")
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
        logger.info(f"Adding stdio server: {server_name} ({command})")
        if server_name in self.servers:
            await self._remove_server(server_name)

        exit_stack = None
        try:
            # Create an exit stack to manage this server's connection lifecycle
            exit_stack = AsyncExitStack()

            # Connect to stdio server with proper error handling
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
            logger.info(f"Stdio server {server_name} added successfully")
        except Exception as e:
            logger.error(f"Failed to add stdio server {server_name}: {e}")
            # Clean up on error with proper task context
            if exit_stack is not None:
                try:
                    await exit_stack.aclose()
                except Exception as cleanup_error:
                    logger.warning(
                        f"Error during cleanup for {server_name}: {cleanup_error}"
                    )
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
        # Save config to file first
        self._save_config_to_file(config)

        mcp_servers = config.get("mcpServers", {})
        logger.info(f"Syncing config with {len(mcp_servers)} servers")

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
            logger.debug(f"Removing outdated server: {server_name}")
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

    async def _remove_server(self, server_name: str) -> None:
        """Remove an MCP server"""
        if server_name not in self.servers:
            return

        logger.info(f"Removing server: {server_name}")

        async with self._shutdown_lock:
            try:
                # First, remove this server from all active sessions
                for session_id, session_info in list(self.sessions.items()):
                    if server_name in session_info.exit_stacks:
                        try:
                            await session_info.exit_stacks[server_name].aclose()
                            del session_info.exit_stacks[server_name]
                        except Exception as e:
                            logger.warning(
                                f"Error closing session for {server_name}: {e}"
                            )

                # Then close the server's main connection with proper error handling
                server_info = self.servers[server_name]
                try:
                    # Give the connection a moment to clean up gracefully
                    await asyncio.sleep(0.1)
                    await server_info.connection_exit_stack.aclose()
                    logger.info(f"Server {server_name} removed successfully")
                except Exception as e:
                    logger.warning(
                        f"Error closing server connection for {server_name}: {e}"
                    )
                    # Don't re-raise here, we still want to remove the server from our dict

                del self.servers[server_name]

            except Exception as e:
                logger.error(f"Unexpected error removing server {server_name}: {e}")
                # Still remove from dict to prevent hanging references
                if server_name in self.servers:
                    del self.servers[server_name]

    async def _close_all_servers(self) -> None:
        """Close all server connections"""
        logger.info("Closing all servers")

        async with self._shutdown_lock:
            # Close all sessions first
            for session_id in list(self.sessions.keys()):
                try:
                    await self.end_session(session_id)
                except Exception as e:
                    logger.warning(f"Error ending session {session_id}: {e}")

            # Then close all server connections
            for server_name in list(self.servers.keys()):
                try:
                    server_info = self.servers[server_name]
                    # Add small delay to allow proper cleanup
                    await asyncio.sleep(0.05)
                    await server_info.connection_exit_stack.aclose()
                    del self.servers[server_name]
                except Exception as e:
                    logger.warning(f"Error closing server {server_name}: {e}")
                    # Remove from dict even if cleanup failed
                    if server_name in self.servers:
                        del self.servers[server_name]

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
        try:
            await self._close_all_servers()
        except Exception as e:
            logger.warning(f"Error during MCPClient cleanup: {e}")
            # Don't re-raise to prevent masking original exceptions


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
):
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
        return {
            "status": "error",
            "message": tool_content,
        }

    return {
        "status": "success",
        "message": tool_content,
        "data": non_text_contents if non_text_contents else None,
    }


def _repair_array_schemas(schema: Dict[str, Any]) -> None:
    """
    Recursively traverse schema dict, and for any 'type: "array"' without 'items',
    add items: {}.
    """
    if not isinstance(schema, dict):
        return
    if schema.get("type") == "array" and "items" not in schema:
        schema["items"] = {}
    # 修复 properties、definitions、patternProperties 下的所有子 schema
    for key in ("properties", "definitions", "patternProperties"):
        subs = schema.get(key)
        if isinstance(subs, dict):
            for subschema in subs.values():
                _repair_array_schemas(subschema)
    # 修复 anyOf/oneOf/allOf
    for key in ("anyOf", "oneOf", "allOf"):
        subs = schema.get(key)
        if isinstance(subs, list):
            for subschema in subs:
                _repair_array_schemas(subschema)
    # 继续修复 items 下的 schema
    items = schema.get("items")
    if isinstance(items, dict):
        _repair_array_schemas(items)


def convert_mcp_tool(
    session: ClientSession,
    tool: Tool,
) -> McpTool:
    # 先深拷贝一份原始的 inputSchema
    raw_schema = tool.inputSchema or {}
    repaired_schema = copy.deepcopy(raw_schema)
    _repair_array_schemas(repaired_schema)

    async def call_tool(
        params: Dict[str, Any],
    ):
        logger.debug(f"Calling tool: {tool.name}")
        call_tool_result = await session.call_tool(tool.name, params)
        return _convert_call_tool_result(call_tool_result)

    return McpTool(
        name=tool.name,
        description=tool.description or "",
        input_schema=repaired_schema,
        annotations=tool.annotations.model_dump() if tool.annotations else None,
        handler=call_tool,
    )


async def load_mcp_tools(
    session: ClientSession,
) -> List[McpTool]:
    tools = await _list_all_tools(session)
    converted_tools = [convert_mcp_tool(session, tool) for tool in tools]
    return converted_tools
