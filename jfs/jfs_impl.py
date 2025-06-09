import io
import os
import stat as stat_mod
import juicefs
from . import FileSystemNode, IOSYSFileSystem
from .service import JuiceFSService


class JuiceFSFileNode(FileSystemNode):
    fs: "JuiceFSFileSystem"

    def __init__(self, fs: "JuiceFSFileSystem", id: str):
        self.fs = fs
        self.type = "file"
        self.path = id
        self.name = os.path.basename(id.rstrip("/"))
        self.meta = {}

    def read_stream(self) -> io.BytesIO:
        if not self.fs.client.exists(self.path):
            raise FileNotFoundError(f"File {self.path} not found.")
        try:
            st = self.fs.client.stat(self.path)
            if stat_mod.S_ISDIR(st.st_mode):
                raise IsADirectoryError(f"{self.path} is a directory.")
        except FileNotFoundError:
            raise
        return self.fs.client.open(self.path, "rb")

    def write(self, content: bytes):
        """Write bytes to file (overwrite)"""
        if not self.fs.client.exists(self.path):
            raise FileNotFoundError(f"File {self.path} not found.")
        try:
            st = self.fs.client.stat(self.path)
            if stat_mod.S_ISDIR(st.st_mode):
                raise IsADirectoryError(f"{self.path} is a directory.")
        except FileNotFoundError:
            raise
        with self.fs.client.open(self.path, "wb") as f:
            f.write(content)
        self.fs.call_file_update(self)

    def remove(self):
        """Remove the file"""
        if not self.fs.client.exists(self.path):
            raise FileNotFoundError(f"File {self.path} not found.")
        try:
            st = self.fs.client.stat(self.path)
            if stat_mod.S_ISDIR(st.st_mode):
                raise IsADirectoryError(f"{self.path} is a directory.")
        except FileNotFoundError:
            raise
        self.fs.client.remove(self.path)
        self.fs.call_file_delete(self)

    def parent(self) -> "JuiceFSDirNode":
        parent_id = os.path.dirname(self.path.rstrip("/"))
        if parent_id == "":
            parent_id = "/"
        return JuiceFSDirNode(self.fs, parent_id)


class JuiceFSDirNode(DirNode):
    fs: "JuiceFSFileSystem"

    def __init__(self, fs: "JuiceFSFileSystem", id: str):
        self.fs = fs
        self.type = "dir"
        self.id = id
        self.name = os.path.basename(id.rstrip("/"))
        self.meta = {}

    def insert_file(self, name: str) -> FileSystemNode:
        """Create a new file in this directory"""
        file_path = os.path.join(self.id, name)
        if self.fs.client.exists(file_path):
            raise FileExistsError(f"File {file_path} already exists.")

        # Create empty file
        with self.fs.client.open(file_path, "wb") as _:
            pass

        node = JuiceFSFileNode(self.fs, file_path)
        self.fs.call_file_update(node)
        return node

    def insert_dir(self, name: str) -> "JuiceFSDirNode":
        """Create a new directory in this directory"""
        dir_path = os.path.join(self.id, name)
        if self.fs.client.exists(dir_path):
            raise FileExistsError(f"Directory {dir_path} already exists.")

        self.fs.client.makedirs(dir_path)
        node = JuiceFSDirNode(self.fs, dir_path)
        self.fs.call_dir_update(node)
        return node

    def remove(self):
        # 递归删除子节点
        for child in self.children():
            child.remove()
        # 删除空目录自身
        self.fs.client.remove(self.path)
        self.fs.call_dir_delete(self)

    def parent(self) -> "JuiceFSDirNode":
        parent_id = os.path.dirname(self.id.rstrip("/"))
        if parent_id == "":
            parent_id = "/"
        return JuiceFSDirNode(self.fs, parent_id)

    def children(self) -> list[FileSystemNode]:
        # Implementation for getting children
        entries = self.fs.client.listdir(self.path)
        nodes = []
        for name in entries:
            full = os.path.join(self.path, name)
            st = self.fs.client.stat(full)
            if stat_mod.S_ISDIR(st.st_mode):
                nodes.append(JuiceFSDirNode(self.fs, full))
            else:
                nodes.append(JuiceFSFileNode(self.fs, full))
        return nodes


class JuiceFSFileSystem(IOSYSFileSystem):
    def __init__(self):
        super().__init__()
        self.service = JuiceFSService()
        self.service.start()

        self.client = juicefs.Client("iosysfilesystem", token=os.environ["JFS_TOKEN"])

    def is_running(self) -> bool:
        return self.service.is_running()

    def get_node(self, id: str) -> FileSystemNode | DirNode | None:
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
