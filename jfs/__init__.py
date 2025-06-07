from typing import Literal, Union, Callable
import abc
import os


class FileNode(abc.ABC):
    fs: "IOSYSFileSystem"
    type: Literal["file"]
    id: str
    name: str
    meta: dict[str, str]

    @abc.abstractmethod
    def read(self) -> bytes:
        """Open the file and read bytes"""
        pass

    @abc.abstractmethod
    def write(self, content: bytes):
        """Write bytes to file (overwrite)"""
        pass

    @abc.abstractmethod
    def remove(self):
        """Remove the file"""
        pass

    @abc.abstractmethod
    def parent(self) -> "DirNode":
        pass

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "meta": self.meta,
        }


class DirNode(abc.ABC):
    fs: "IOSYSFileSystem"
    type: Literal["dir"]
    id: str
    name: str
    meta: dict[str, str]

    @abc.abstractmethod
    def insert(self, node: Union[FileNode, "DirNode"]): ...

    @abc.abstractmethod
    def remove(self): ...

    @abc.abstractmethod
    def parent(self) -> "DirNode": ...

    @abc.abstractmethod
    def children(self) -> list[Union[FileNode, "DirNode"]]: ...

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "meta": self.meta,
        }


class IOSYSFileSystem(abc.ABC):
    on_file_update: list[Callable[[FileNode], None]] = []
    on_file_delete: list[Callable[[FileNode], None]] = []
    on_dir_update: list[Callable[[DirNode], None]] = []
    on_dir_delete: list[Callable[[DirNode], None]] = []

    @abc.abstractmethod
    def is_running(self) -> bool: ...

    @abc.abstractmethod
    def get_node(self, id: str) -> Union[FileNode, DirNode, None]: ...

    @abc.abstractmethod
    def exists(self, id: str) -> bool: ...

    def get_file_node(self, id: str) -> Union[FileNode, None]:
        node = self.get_node(id)
        if not node or node.type != "file":
            return None
        return node

    def get_dir_node(self, id: str) -> Union[DirNode, None]:
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


def new_fs() -> IOSYSFileSystem:
    use_local_fs = os.environ.get("USE_LOCAL_FS")
    if use_local_fs:
        from .osfs_impl import OSFileSystem

        return OSFileSystem(root_path=use_local_fs)
    else:
        from .jfs_impl import JuiceFSFileSystem

        return JuiceFSFileSystem()
