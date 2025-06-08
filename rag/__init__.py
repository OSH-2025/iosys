import threading

from jfs import FileSystemNode, IOSYSFileSystem
from parser import IOSYSParser

from .query import IOSYSQueryEngine
from .graph import IOSYSGraphEngine


class IOSYSRAG:
    fs: IOSYSFileSystem
    parser: IOSYSParser
    query: IOSYSQueryEngine
    graph: IOSYSGraphEngine
    _dump_timer: threading.Timer

    def __init__(self, fs: IOSYSFileSystem):
        self.fs = fs
        self.fs.on_change.append(self.on_fs_change)
        self.parser = IOSYSParser()
        self.query = IOSYSQueryEngine()
        self.graph = IOSYSGraphEngine()

    async def on_fs_change(self, node: FileSystemNode):
        # TODO:
        await self.update_file(node)

    async def update_file(self, node: FileSystemNode):
        parsed = self.parser.parse(node)
        await self.query.update_file(node.path, parsed)
        await self.graph.update_file(node.path, parsed)

    async def delete_file(self, node: FileSystemNode):
        await self.query.delete_file(node.path)
        await self.graph.delete_file(node.path)

    async def update_dir(self, node: FileSystemNode): ...

    async def delete_dir(self, node: FileSystemNode): ...
