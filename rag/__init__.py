import json
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
        self._start_periodic_dump()

    def load(self):
        try:
            dumped = self.fs.read("__graph__.json")
            if dumped:
                self.graph.load(json.loads(dumped.decode("utf-8")))
        except FileNotFoundError:
            pass

    def dump(self):
        dumped = json.dumps(self.graph.dump())
        file_node = self.fs.get_node("__graph__.json")
        if not file_node:
            file_node = self.fs.get_root().insert_node("__graph__.json")
        file_node.write(dumped.encode("utf-8"))

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

    def _start_periodic_dump(self):
        """Start periodic dumping every 10 seconds"""
        self._dump_timer = threading.Timer(10.0, self._periodic_dump)
        self._dump_timer.daemon = True
        self._dump_timer.start()

    def _periodic_dump(self):
        """Perform dump and schedule next dump"""
        print("Periodic dump of the graph")
        self.dump()
        self._start_periodic_dump()

    def stop_periodic_dump(self):
        """Stop the periodic dumping"""
        if hasattr(self, "_dump_timer"):
            self._dump_timer.cancel()
