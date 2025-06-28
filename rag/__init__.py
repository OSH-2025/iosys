import threading
import os

from fs import FileSystemNode, IOSYSFileSystem, CHANGE_TYPE
from parser import IOSYSParser
from llama_index.llms.openai import OpenAI

from .query import IOSYSQueryEngine
from .file_graph import IOSYSGraphEngine


class IOSYSRAG:
    fs: IOSYSFileSystem
    parser: IOSYSParser
    query: IOSYSQueryEngine
    graph: IOSYSGraphEngine
    _dump_timer: threading.Timer

    def __init__(self, fs: IOSYSFileSystem, parser: IOSYSParser):
        self.fs = fs
        self.fs.on_change.append(self.on_fs_change)

        self.parser = parser

        llm = OpenAI(
            api_base=os.environ["LLM_BASE_URL"],
            api_key=os.environ["LLM_API_KEY"],
            model=os.environ["LLM_MODEL_NAME"],
        )
        self.query = IOSYSQueryEngine(llm)
        self.graph = IOSYSGraphEngine(llm)

    async def on_fs_change(self, node: FileSystemNode, change_type: CHANGE_TYPE):
        match node.get_meta("type"):
            case "file":
                await self.on_file_change(node, change_type)
            case "directory":
                await self.on_directory_change(node, change_type)
            case "embedded":
                await self.on_embedded_change(node, change_type)
            case _:
                raise ValueError(f"Unsupported node type: {node.get_meta('type')}")

    async def on_file_change(self, node: FileSystemNode, change_type: CHANGE_TYPE):
        match change_type:
            case "create":
                parsed = self.parser.parse(node)
                await self.query.create_node(node.path, parsed)
                await self.graph.create_file(node.path, parsed)
            case "update":
                parsed = self.parser.parse(node)
                await self.query.update_node(node.path, parsed)
                await self.graph.update_file(node.path, parsed)
            case "delete":
                await self.query.delete_node(node.path)
                await self.graph.delete_file(node.path)

    async def on_directory_change(self, node: FileSystemNode, change_type: CHANGE_TYPE):
        parent = node.parent()
        if not parent:
            return
        parent_path = parent.path
        match change_type:
            case "create":
                await self.graph.create_directory(node.path, parent_path)
            case "update":
                await self.graph.update_directory(node.path, parent_path)
            case "delete":
                await self.graph.delete_directory(node.path)

    async def on_embedded_change(self, node: FileSystemNode, change_type: CHANGE_TYPE):
        raise NotImplementedError()
