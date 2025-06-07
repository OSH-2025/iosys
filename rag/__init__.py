import json
import threading

from jfs import FileNode, IOSYSFileSystem
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
        self.fs.on_file_update.append(self.update_file)
        self.fs.on_file_delete.append(self.delete_file)
        self.fs.on_dir_update.append(self.update_dir)
        self.fs.on_dir_delete.append(self.delete_dir)
        self.parser = IOSYSParser()
        self.query = IOSYSQueryEngine()
        self.graph = IOSYSGraphEngine()
        self._start_periodic_dump()

    def load(self):
        if self.fs.exists("__graph__.json"):
            dumped = self.fs.read("__graph__.json")
            if dumped:
                self.graph.load(json.loads(dumped.decode("utf-8")))

    def dump(self):
        dumped = json.dumps(self.graph.dump())
        file_node = self.fs.get_file_node("__graph__.json")
        if not file_node:
            file_node = self.fs.get_dir_node("/").insert_file("__graph__.json")
        file_node.write(dumped.encode("utf-8"))

    async def update_file(self, node: FileNode):
        parsed = self.parser.parse(node)
        await self.query.update_file(node.id, parsed)
        await self.graph.update_file(node.id, parsed)

    async def delete_file(self, node: FileNode):
        await self.query.delete_file(node.id)
        await self.graph.delete_file(node.id)

    async def update_dir(self, node: FileNode): ...

    async def delete_dir(self, node: FileNode): ...

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
