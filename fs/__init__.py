import asyncio
from typing import Awaitable, Callable, Literal, Union, overload
import abc
import os
import io

from utils.logger import IOSYSLogger


class FileSystemNode(abc.ABC):
    fs: "IOSYSFileSystem"
    # Must start with a slash, and not end with a slash
    # Must use forward slashes
    # e.g. "/path/to/file.txt" or "/path/to/directory"
    path: str
    _meta: dict[str, str | int | float | bool]

    def __init__(self, fs: "IOSYSFileSystem", path: str):
        self.path = path
        self.fs = fs
        self.path = path
        self._meta = {}

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
        """Make the node a file node, and write bytes to file (overwrite)"""
        pass

    @abc.abstractmethod
    def makedir(self):
        """Make the node a directory node"""
        pass

    @abc.abstractmethod
    def remove(self):
        """Remove the node itself"""
        pass

    @abc.abstractmethod
    def move_to(self, dst_path: str):
        """Move the node to a new directory (may be a file or directory)"""
        pass

    @abc.abstractmethod
    def parent(self) -> Union["FileSystemNode", None]:
        """Get the parent node of this node"""
        pass

    @abc.abstractmethod
    def children(self) -> list["FileSystemNode"]:
        """List children of this node"""
        pass

    @abc.abstractmethod
    def create_child(self, name: str) -> "FileSystemNode":
        """Create a new child node (may be a file or directory)"""
        pass

    @overload
    def get_meta(self, key: str) -> Union[str, int, float, bool, None]: ...
    @overload
    def get_meta(
        self, key: str, default: Union[str, int, float, bool]
    ) -> Union[str, int, float, bool]: ...
    def get_meta(
        self, key: str, default: Union[str, int, float, bool, None] = None
    ) -> Union[str, int, float, bool, None]:
        """Get metadata of the node"""
        return self._meta.get(key, default)

    def update_meta(self, **kwargs):
        """Update metadata of the node"""
        self._meta.update(kwargs)
        self._sync_metadata()

    @abc.abstractmethod
    def _sync_metadata(self):
        """Synchronize metadata with the underlying file system"""
        pass

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "name": self.name,
            "meta": self._meta,
        }


CHANGE_TYPE = Literal["create", "update", "delete", "metadata"]


class IOSYSFileSystem(abc.ABC):
    on_change: list[Callable[[FileSystemNode, CHANGE_TYPE], Awaitable[None]]]

    _previous_task: asyncio.Task | None = None

    def __init__(self):
        logger = IOSYSLogger("FS")

        async def log_callback(node: FileSystemNode, change_type: CHANGE_TYPE):
            logger.info(f"{change_type} {node.path}")

        self.on_change = [log_callback]

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
        """A convenience method to write bytes to a file. If the file does not exist, it will be created."""
        node = self.get_node(path)
        if node:
            node.write(content)
            return node
        segmented_path = [seg for seg in self.normalize_path(path).lstrip("/").split("/") if seg]
        if not segmented_path:
            raise ValueError("Cannot write to root directory.")
        dir_name = "/".join(segmented_path[:-1]) + "/"
        file_name = segmented_path[-1]
        dir_node = self.ensure_directory(dir_name)
        node = dir_node.create_child(file_name)
        node.write(content)
        return node

    def ensure_directory(self, path: str) -> FileSystemNode:
        """A convenience method to ensure a directory exists at the specified path."""
        node = self.get_node(path)
        if node:
            if node.get_meta("type", "directory") != "directory":
                raise ValueError(f"Path {path} is not a directory.")
            return node
        segmented_path = [seg for seg in self.normalize_path(path).lstrip("/").split("/") if seg]
        dir_path = ""
        dir_node = self.get_root()
        for segment in segmented_path:
            dir_path = dir_path + "/" + segment
            node = self.get_node(dir_path)
            if not node:
                node = dir_node.create_child(segment)
            node.makedir()
            dir_node = node
        return dir_node

    def create_directory(self, path: str) -> FileSystemNode:
        """Create a directory at the specified path."""
        segmented_path = [seg for seg in self.normalize_path(path).lstrip("/").split("/") if seg]
        if not segmented_path:
            raise ValueError("Cannot write to root directory.")
        dir_name = "/".join(segmented_path[:-1]) + "/"
        create_dir_name = segmented_path[-1]
        dir_node = self.ensure_directory(dir_name)
        node = dir_node.create_child(create_dir_name)
        node.makedir()
        return node

    def remove(self, path: str):
        """A convenience method to remove a file or directory at the specified path."""
        node = self.get_node(path)
        if not node:
            raise FileNotFoundError(f"Node {path} not found.")
        node.remove()

    def move(self, src_path: str, dst_path: str):
        """Move a directory to a new location"""
        src_node = self.get_node(src_path)
        if not src_node:
            raise FileNotFoundError(f"Source node {src_path} not found.")
        src_node.move_to(dst_path)

    def fire_event(self, change_type: CHANGE_TYPE, node: FileSystemNode):
        if not self.on_change:
            return

        previous_task = self._previous_task

        async def execute_callbacks():
            if previous_task and not previous_task.done():
                await previous_task
            await asyncio.gather(
                *[callback(node, change_type) for callback in self.on_change],
                return_exceptions=False,
            )

        self._previous_task = asyncio.create_task(execute_callbacks())

    def normalize_path(self, path: str) -> str:
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
