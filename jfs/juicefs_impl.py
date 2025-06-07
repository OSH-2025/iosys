import os
import stat as stat_mod
import juicefs
from . import FileNode, DirNode, IOSYSFileSystem
from .service import JuiceFSService


class JuiceFSFileNode(FileNode):
    fs: "JuiceFSFileSystem"

    def __init__(self, fs: "JuiceFSFileSystem", id: str):
        self.fs = fs
        self.type = "file"
        self.id = id
        self.name = os.path.basename(id.rstrip("/"))
        self.meta = {}

    def read(self) -> bytes:
        """Open the file and read bytes"""
        if not self.fs.client.exists(self.id):
            raise FileNotFoundError(f"File {self.id} not found.")
        try:
            st = self.fs.client.stat(self.id)
            if stat_mod.S_ISDIR(st.st_mode):
                raise IsADirectoryError(f"{self.id} is a directory.")
        except FileNotFoundError:
            raise
        with self.fs.client.open(self.id, "rb") as f:
            return f.read()

    def write(self, content: bytes):
        """Write bytes to file (overwrite)"""
        if not self.fs.client.exists(self.id):
            raise FileNotFoundError(f"File {self.id} not found.")
        try:
            st = self.fs.client.stat(self.id)
            if stat_mod.S_ISDIR(st.st_mode):
                raise IsADirectoryError(f"{self.id} is a directory.")
        except FileNotFoundError:
            raise
        with self.fs.client.open(self.id, "wb") as f:
            f.write(content)
        self.fs.call_file_update(self)

    def remove(self):
        """Remove the file"""
        if not self.fs.client.exists(self.id):
            raise FileNotFoundError(f"File {self.id} not found.")
        try:
            st = self.fs.client.stat(self.id)
            if stat_mod.S_ISDIR(st.st_mode):
                raise IsADirectoryError(f"{self.id} is a directory.")
        except FileNotFoundError:
            raise
        self.fs.client.remove(self.id)
        self.fs.call_file_delete(self)

    def parent(self) -> "JuiceFSDirNode":
        parent_id = os.path.dirname(self.id.rstrip("/"))
        if parent_id == "":
            parent_id = "/"
        return JuiceFSDirNode(self.fs, parent_id)


class JuiceFSDirNode(DirNode):
    def __init__(self, fs: "JuiceFSFileSystem", id: str):
        self.fs = fs
        self.type = "dir"
        self.id = id
        self.name = os.path.basename(id.rstrip("/"))
        self.meta = {}

    def insert(self, node: FileNode | DirNode):
        # Implementation for inserting nodes
        pass

    def remove(self):
        # Implementation for removing directory
        pass

    def parent(self) -> "JuiceFSDirNode":
        parent_id = os.path.dirname(self.id.rstrip("/"))
        if parent_id == "":
            parent_id = "/"
        return JuiceFSDirNode(self.fs, parent_id)

    def children(self) -> list[FileNode]:
        # Implementation for getting children
        return []


class JuiceFSFileSystem(IOSYSFileSystem):
    def __init__(self):
        super().__init__()
        self.service = JuiceFSService()
        self.service.start()

        self.client = juicefs.Client(
            name=os.environ.get("JFS_NAME"),
            meta=os.environ.get("JFS_META_URL"),
        )

    def get_node(self, id: str) -> FileNode | DirNode | None:
        if not self.exists(id):
            return None

        try:
            st = self.client.stat(id)
            if stat_mod.S_ISDIR(st.st_mode):
                return JuiceFSDirNode(self, id)
            else:
                return JuiceFSFileNode(self, id)
        except FileNotFoundError:
            return None

    def exists(self, id: str) -> bool:
        return self.client.exists(id)
