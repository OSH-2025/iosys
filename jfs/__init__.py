import asyncio
from typing import Awaitable, Callable, Literal, Union
import abc
import os
import io


class FileSystemNode(abc.ABC):
    fs: "IOSYSFileSystem"
    # Must start with a slash, and not end with a slash
    # Must use forward slashes
    # e.g. "/path/to/file.txt" or "/path/to/directory"
    path: str
    meta: dict[str, str | int | float | bool]

    def __init__(self, fs: "IOSYSFileSystem", path: str):
        self.path = path
        self.fs = fs
        self.path = path
        self.meta = {}

    @property
    def name(self) -> str:
        """Get the name of the node"""
        return os.path.basename(self.path)

    @abc.abstractmethod
    def read_stream(self) -> io.BytesIO:
        """Open the file and return a stream"""
        pass

    def read(self) -> bytes:
        """Open the file and read bytes"""
        stream = self.read_stream()
        content = stream.read()
        stream.close()
        return content

    @abc.abstractmethod
    def write(self, content: bytes):
        """Write bytes to file (overwrite)"""
        pass

    @abc.abstractmethod
    def remove(self):
        """Remove the node itself"""
        pass

    @abc.abstractmethod
    def parent(self) -> Union["FileSystemNode", None]:
        pass

    @abc.abstractmethod
    def children(self) -> list["FileSystemNode"]:
        """List children of this node, if applicable"""
        pass

    @abc.abstractmethod
    def create_child(self, name: str) -> "FileSystemNode":
        """Create a new node in this directory"""
        pass

    def update_meta(self, **kwargs):
        """Update metadata of the node"""
        self.meta.update(kwargs)
        self._sync_metadata()

    @abc.abstractmethod
    def _sync_metadata(self):
        """Synchronize metadata with the underlying file system"""
        pass

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "name": self.name,
            "meta": self.meta,
        }


CHANGE_TYPE = Literal["create", "update", "delete", "metadata"]


class IOSYSFileSystem(abc.ABC):
    on_change: list[Callable[[FileSystemNode, CHANGE_TYPE], Awaitable[None]]] = []
    _pending_changes: dict[str, asyncio.Task] = {}

    @abc.abstractmethod
    def is_running(self) -> bool: ...

    @abc.abstractmethod
    def get_node(self, path: str) -> FileSystemNode | None: ...

    def get_root(self) -> FileSystemNode:
        """Get the root node of the file system"""
        root = self.get_node("/")
        if not root:
            raise FileNotFoundError("Root node not found.")
        return root

    def read(self, path: str) -> bytes:
        node = self.get_node(path)
        if not node:
            raise FileNotFoundError(f"File {path} not found.")
        return node.read()

    def write_file(self, path: str, content: bytes) -> FileSystemNode:
        node = self.get_node(path)
        if node:
            node.write(content)
            return node
        segmented_path = self._normalize_path(path).split("/")
        if not segmented_path:
            raise ValueError("Cannot write to root directory.")
        dir_name = "/".join(segmented_path[:-1]) + "/"
        file_name = segmented_path[-1]
        dir_node = self.ensure_directory(dir_name)
        node = dir_node.create_child(file_name)
        node.write(content)
        return node

    def ensure_directory(self, path: str) -> FileSystemNode:
        node = self.get_node(path)
        if node:
            if node.meta.get("type") != "directory":
                raise ValueError(f"Path {path} is not a directory.")
            return node
        segmented_path = self._normalize_path(path).split("/")
        dir_path = ""
        dir_node = self.get_root()
        for segment in segmented_path:
            dir_path = dir_path + "/" + segment
            node = self.get_node(dir_path)
            if not node:
                node = dir_node.create_child(segment)
            dir_node = node
        return dir_node

    def remove(self, path: str):
        node = self.get_node(path)
        if not node:
            raise FileNotFoundError(f"Node {path} not found.")
        node.remove()

    def invoke_on_change(self, node: FileSystemNode, change_type: CHANGE_TYPE):
        if not self.on_change:
            return

        # 使用节点路径作为 key 进行 debounce
        key = node.path

        # 取消之前的任务
        if key in self._pending_changes:
            self._pending_changes[key].cancel()

        async def execute_callbacks():
            await asyncio.sleep(0.1)  # 100ms debounce
            await asyncio.gather(
                *[callback(node, change_type) for callback in self.on_change]
            )
            self._pending_changes.pop(key, None)

        self._pending_changes[key] = asyncio.create_task(execute_callbacks())

    def _normalize_path(self, path: str) -> str:
        path = path.strip().replace("\\", "/").replace("//", "/")
        path = path.rstrip("/")
        if not path.startswith("/"):
            path = "/" + path
        return path


def new_fs() -> IOSYSFileSystem:
    use_local_fs = os.environ.get("USE_LOCAL_FS")
    if use_local_fs:
        from .osfs_impl import OSFileSystem

        return OSFileSystem(root_path=use_local_fs)
    else:
        from .jfs_impl import JuiceFSFileSystem

        return JuiceFSFileSystem()
