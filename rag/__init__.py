from ..jfs import FileSystemNode, IOSYSFileSystem
from ..parser import IOSYSParser
from .engine import IOSYSQueryEngine


class IOSYSRAG:
    filesystem: IOSYSFileSystem
    parser: IOSYSParser
    engine: IOSYSQueryEngine

    def __init__(self):
        self.filesystem = IOSYSFileSystem(
            on_file_update=self.update_file,
            on_file_delete=self.delete_file,
            on_dir_update=self.update_dir,
            on_dir_delete=self.delete_dir,
        )
        self.parser = IOSYSParser()
        self.engine = IOSYSQueryEngine()
        if self.filesystem.exists("__graph__.json"):
            dumped = self.filesystem.read("__graph__.json")
            self.engine.load(dumped)

    def update_file(self, file_path: FileSystemNode, content: str):
        parsed = self.parser.parse(file_path, content)
        self.engine.update_file(file_path, parsed)
