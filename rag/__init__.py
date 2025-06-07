from jfs import FileNode, IOSYSFileSystem
from parser import IOSYSParser

from .query import IOSYSQueryEngine
from .graph import IOSYSGraphEngine


class IOSYSRAG:
    fs: IOSYSFileSystem
    parser: IOSYSParser
    query: IOSYSQueryEngine
    graph: IOSYSGraphEngine

    def __init__(self, fs: IOSYSFileSystem):
        self.fs = fs
        self.fs.on_file_update.append(self.update_file)
        self.fs.on_file_delete.append(self.delete_file)
        self.fs.on_dir_update.append(self.update_file)
        self.fs.on_dir_delete.append(self.delete_file)
        self.parser = IOSYSParser()
        self.query = IOSYSQueryEngine()
        self.graph = IOSYSGraphEngine()

    def load(self):
        if self.fs.exists("__graph__.json"):
            dumped = self.fs.read("__graph__.json")
            self.graph.load(dumped.decode("utf-8"))

    def dump(self):
        dumped = self.graph.dump()
        self.fs.write("__graph__.json", dumped.encode("utf-8"))

    def update_file(self, node: FileNode):
        parsed = self.parser.parse(node)
        self.query.update_file(node.id, parsed)
        self.graph.update_file(node.id, parsed)

    def delete_file(self, node: FileNode):
        self.query.delete_file(node.id)
        self.graph.delete_file(node.id)
