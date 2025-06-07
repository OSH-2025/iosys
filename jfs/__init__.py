from typing import Literal
import os
import stat as stat_mod
import juicefs


class FileNode:
    fs: "IOSYSFileSystem"
    type: Literal["file"]
    id: str
    meta: dict[str, str]

    def read(self) -> bytes:
        """
        Open the file and read bytes
        """
        if not self.fs.jfs.exists(self.id):
            raise FileNotFoundError(f"File {self.id} not found.")
        try:
            st = self.fs.jfs.stat(self.id)
            if stat_mod.S_ISDIR(st.st_mode):
                raise IsADirectoryError(f"{self.id} is a directory.")
        except FileNotFoundError:
            raise
        with self.fs.jfs.open(self.id, "rb") as f:
            return f.read()

    def write(self, content: bytes):
        """
        Write bytes to file (overwrite)
        """
        if not self.fs.jfs.exists(self.id):
            raise FileNotFoundError(f"File {self.id} not found.")
        try:
            st = self.fs.jfs.stat(self.id)
            if stat_mod.S_ISDIR(st.st_mode):
                raise IsADirectoryError(f"{self.id} is a directory.")
        except FileNotFoundError:
            raise
        with self.fs.jfs.open(self.id, "wb") as f:
            f.write(content)
        # Trigger update callback
        self.fs.call_file_update(self)

    def remove(self):
        """
        Remove the file
        """
        if not self.fs.jfs.exists(self.id):
            raise FileNotFoundError(f"File {self.id} not found.")
        try:
            st = self.fs.jfs.stat(self.id)
            if stat_mod.S_ISDIR(st.st_mode):
                raise IsADirectoryError(f"{self.id} is a directory.")
        except FileNotFoundError:
            raise
        self.fs.jfs.remove(self.id)
        self.fs.call_file_delete(self)

    def parent(self) -> "DirNode":
        parent_id = os.path.dirname(self.id.rstrip("/"))
        if parent_id == "":
            parent_id = "/"
        return DirNode(self.fs, parent_id)


class DirNode:
    fs: "IOSYSFileSystem"
    type: Literal["dir"]
    id: str
    meta: dict[str, str]

    def insert(self, node: FileNode | "DirNode"): ...
    # Remove the directory itself
    def remove(self): ...

    def parent(self) -> "DirNode": ...
    def children(self) -> list[FileNode]: ...


class IOSYSFileSystem:
    on_file_update: list[callable[[FileNode], None]]
    on_file_delete: list[callable[[FileNode], None]]
    on_dir_update: list[callable[[DirNode], None]]
    on_dir_delete: list[callable[[DirNode], None]]

    def get_node(self, id: str) -> FileNode | DirNode | None: ...
    def exists(self, id: str) -> bool: ...

    def get_file_node(self, id: str) -> FileNode | None:
        node = self.get_node(id)
        if not node or node.type != "file":
            return None
        return node

    def get_dir_node(self, id: str) -> DirNode | None:
        node = self.get_node(id)
        if not node or node.type != "dir":
            return None
        return node

    def read(self, id: str) -> bytes:
        node = self.get_file_node(id)
        if not node:
            raise FileNotFoundError(f"File {id} not found.")
        return node.read()

    def write(self, id: str, content: bytes):
        node = self.get_file_node(id)
        if not node:
            raise FileNotFoundError(f"File {id} not found.")
        node.write(content)

    def remove(self, id: str):
        node = self.get_node(id)
        if not node:
            raise FileNotFoundError(f"Node {id} not found.")
        node.remove()

    def call_file_update(self, node: FileNode):
        for callback in self.on_file_update:
            callback(node)

    def call_file_delete(self, node: FileNode):
        for callback in self.on_file_delete:
            callback(node)

    def call_dir_update(self, node: DirNode):
        for callback in self.on_dir_update:
            callback(node)

    def call_dir_delete(self, node: DirNode):
        for callback in self.on_dir_delete:
            callback(node)
