from __future__ import annotations

import io
import os
import stat as stat_mod
from typing import List, Union

import juicefs  # type: ignore

from . import FileSystemNode, IOSYSFileSystem  # Assuming DirNode is defined elsewhere
from .service import JuiceFSService
from utils.logger import IOSYSLogger

"""
import io
import os
import stat as stat_mod
import juicefs
from . import FileSystemNode, IOSYSFileSystem
from .service import JuiceFSService
"""
'''
class JuiceFSFileNode(FileSystemNode):
    fs: "JuiceFSFileSystem"

    def __init__(self, fs: "JuiceFSFileSystem", path: str):
        self.fs = fs
        self.type = "file"
        self.path = path.rstrip("/") or "/"
        self.name = self.path.rstrip("/").split("/")[-1] or "/"
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
'''

"""JuiceFS-backed implementation of IOSYSFileSystem.

This module rewrites and completes the previous partial implementation,
following the latest JuiceFS Python‑SDK usage pattern documented in the
JuiceFS official docs.
"""


###########################################################################
# Helper functions
###########################################################################


def _norm(path: str) -> str:
    """Normalize a path to ensure leading slash *without* trailing slash (except root)."""
    path = path.strip().replace("\\", "/").replace("//", "/")
    if not path.startswith("/"):
        path = "/" + path
    if path != "/":
        path = path.rstrip("/")
    return path or "/"


###########################################################################
# JuiceFS node types
###########################################################################


class JuiceFSFileNode(FileSystemNode):
    """A file node stored in JuiceFS."""

    def __init__(self, fs: "JuiceFSFileSystem", path: str):
        super().__init__(fs, _norm(path))
        self.meta["type"] = "file"
        # self.fs = cast("JuiceFSFileSystem", fs)

    # ------------------------------------------------------------------
    # File‑specific operations
    # ------------------------------------------------------------------
    def read_stream(self) -> io.BytesIO:  # type: ignore[override]
        if not self.fs.client.exists(self.path):
            raise FileNotFoundError(self.path)
        return self.fs.client.open(self.path, "rb")

    def write(self, content: bytes):  # type: ignore[override]
        with self.fs.client.open(self.path, "wb") as fp:
            fp.write(content)
        self.fs._notify_change(self, "update")

    def makedir(self):  # type: ignore[override]
        raise IsADirectoryError(self.path)

    def remove(self):  # type: ignore[override]
        self.fs.client.remove(self.path)
        self.fs._notify_change(self, "delete")

    # ------------------------------------------------------------------
    # Hierarchy helpers
    # ------------------------------------------------------------------
    def parent(self) -> "JuiceFSDirNode":  # type: ignore[override]
        return JuiceFSDirNode(self.fs, os.path.dirname(self.path))

    def children(self) -> List[FileSystemNode]:  # type: ignore[override]
        return []  # files have no children

    def create_child(self, name: str):  # type: ignore[override]
        raise IsADirectoryError(self.path)

    # ------------------------------------------------------------------
    def _sync_metadata(self):  # type: ignore[override]
        # Metadata persistence can be done via extended attributes later.
        pass


class JuiceFSDirNode(FileSystemNode):
    """A directory node in JuiceFS."""

    def __init__(self, fs: "JuiceFSFileSystem", path: str):
        super().__init__(fs, _norm(path))
        self.meta["type"] = "directory"

    # ------------------------------------------------------------------
    # Directory‑specific ops
    # ------------------------------------------------------------------
    def read_stream(self):  # type: ignore[override]
        raise IsADirectoryError(self.path)

    def write(self, content: bytes):  # type: ignore[override]
        raise IsADirectoryError(self.path)

    def makedir(self):  # type: ignore[override]
        if not self.fs.client.exists(self.path):
            self.fs.client.makedirs(self.path)
            self.fs._notify_change(self, "create")

    def remove(self):  # type: ignore[override]
        # SDK 5.2+ provides rmr (recursive remove); fall back otherwise.
        if hasattr(self.fs.client, "rmr"):
            self.fs.client.rmr(self.path)
        else:
            # Manual recursive deletion
            for child in self.children():
                child.remove()
            if self.path != "/":
                self.fs.client.remove(self.path)
        self.fs._notify_change(self, "delete")

    # ------------------------------------------------------------------
    # Hierarchy helpers
    # ------------------------------------------------------------------
    def parent(self) -> "JuiceFSDirNode":  # type: ignore[override]
        if self.path == "/":
            return self  # root's parent is itself
        return JuiceFSDirNode(self.fs, os.path.dirname(self.path))

    def children(self) -> List[FileSystemNode]:  # type: ignore[override]
        try:
            names = self.fs.client.listdir(self.path)
        except FileNotFoundError:
            return []
        nodes: List[FileSystemNode] = []
        for name in names:
            full_path = os.path.join(self.path if self.path != "/" else "", name)
            node = self.fs.get_node(full_path)
            if node:
                nodes.append(node)
        return nodes

    def create_child(self, name: str) -> FileSystemNode:  # type: ignore[override]
        child_path = os.path.join(self.path if self.path != "/" else "", name)
        # Return node *without* creating it physically; caller will decide.
        return JuiceFSDirNode(self.fs, child_path)

    # ------------------------------------------------------------------
    def insert_file(self, name: str) -> "JuiceFSFileNode":
        """Convenience helper mirroring original API."""
        file_path = os.path.join(self.path if self.path != "/" else "", name)
        if self.fs.client.exists(file_path):
            raise FileExistsError(file_path)
        with self.fs.client.open(file_path, "wb"):
            pass  # create empty file
        node = JuiceFSFileNode(self.fs, file_path)
        self.fs._notify_change(node, "create")
        return node

    def insert_dir(self, name: str) -> "JuiceFSDirNode":
        dir_path = os.path.join(self.path if self.path != "/" else "", name)
        if self.fs.client.exists(dir_path):
            raise FileExistsError(dir_path)
        self.fs.client.makedirs(dir_path)
        node = JuiceFSDirNode(self.fs, dir_path)
        self.fs._notify_change(node, "create")
        return node

    # ------------------------------------------------------------------
    def _sync_metadata(self):  # type: ignore[override]
        # TODO: write directory metadata via xattrs when JuiceFS supports it
        pass


###########################################################################
# File system wrapper
###########################################################################


class JuiceFSFileSystem(IOSYSFileSystem):
    """IOSYSFileSystem implementation backed by JuiceFS Python SDK."""

    def __init__(self):
        super().__init__()
        self.logger = IOSYSLogger("JuiceFS")

        # Spawn side‑car service if needed (e.g., HTTP API to remote JFS).
        self.service = JuiceFSService()
        self.service.start()

        # Initialise client – supports either native conf or explicit meta URL.
        name = os.getenv("JFS_NAME")
        meta = os.getenv("JFS_META_URL")
        token = os.getenv("JFS_TOKEN")
        access_key = os.getenv("JFS_ACCESS_KEY")
        secret_key = os.getenv("JFS_SECRET_KEY")

        kwargs = {}
        if meta:
            kwargs["meta"] = meta
        if token:
            kwargs["token"] = token
        if access_key and secret_key:
            kwargs["access_key"] = access_key
            kwargs["secret_key"] = secret_key

        self.client = juicefs.Client(name, **kwargs)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # IOSYSFileSystem interface
    # ------------------------------------------------------------------
    def is_running(self) -> bool:  # type: ignore[override]
        return self.service.is_running()

    def get_node(self, path: str) -> Union[FileSystemNode, None]:  # type: ignore[override]
        norm = _norm(path)
        if not self.client.exists(norm):
            return None
        st = self.client.stat(norm)
        if stat_mod.S_ISDIR(st.st_mode):
            return JuiceFSDirNode(self, norm)
        return JuiceFSFileNode(self, norm)

    def exists(self, path: str) -> bool:
        return self.client.exists(_norm(path))

    # ------------------------------------------------------------------
    # Change notification helpers (mirrors original call_* helpers)
    # ------------------------------------------------------------------
    def _notify_change(self, node: FileSystemNode, change_type: str):
        self.invoke_on_change(node, change_type)  # inherited

    # Aliases for compatibility with earlier codebase
    def call_file_update(self, node: FileSystemNode):
        self._notify_change(node, "update")

    def call_file_delete(self, node: FileSystemNode):
        self._notify_change(node, "delete")

    def call_dir_update(self, node: FileSystemNode):
        self._notify_change(node, "update")

    def call_dir_delete(self, node: FileSystemNode):
        self._notify_change(node, "delete")


###########################################################################
# Public factory hook (optional)
###########################################################################


def new_fs() -> IOSYSFileSystem:  # noqa: D401 – factory method
    """Return a ready‑to‑use JuiceFS‑backed file system."""
    return JuiceFSFileSystem()
