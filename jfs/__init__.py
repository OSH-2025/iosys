from typing import Literal


class FileNode:
    fs: "IOSYSFileSystem"
    type: Literal["file"]
    id: str
    meta: dict[str, str]

    def read(self) -> bytes: ...
    def write(self, content: bytes): ...
    def remove(self): ...

    def parent(self) -> "DirNode": ...


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
