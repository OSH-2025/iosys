from __future__ import annotations

import io
import os
import stat as stat_mod
from typing import List, Union, cast

import juicefs  # type: ignore

from . import (
    FileSystemNode,
    IOSYSFileSystem,
    CHANGE_TYPE,
)  # Assuming DirNode is defined elsewhere
from .service import JuiceFSService
from utils.logger import IOSYSLogger


def _norm(path: str) -> str:
    """Normalize a path to ensure leading slash *without* trailing slash (except root)."""
    path = path.strip().replace("\\", "/").replace("//", "/")
    if not path.startswith("/"):
        path = "/" + path
    if path != "/":
        path = path.rstrip("/")
    return path or "/"


class JuiceFSFileNode(FileSystemNode):
    """A file node stored in JuiceFS."""

    def __init__(self, fs: "JuiceFSFileSystem", path: str):
        super().__init__(fs, _norm(path))
        self.meta["type"] = "file"

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
        return JuiceFSDirNode(
            cast("JuiceFSFileSystem", self.fs), os.path.dirname(self.path)
        )

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
        return JuiceFSDirNode(
            cast("JuiceFSFileSystem", self.fs), os.path.dirname(self.path)
        )

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
        return JuiceFSDirNode(cast("JuiceFSFileSystem", self.fs), child_path)

    # ------------------------------------------------------------------
    def insert_file(self, name: str) -> "JuiceFSFileNode":
        """Convenience helper mirroring original API."""
        file_path = os.path.join(self.path if self.path != "/" else "", name)
        if self.fs.client.exists(file_path):
            raise FileExistsError(file_path)
        with self.fs.client.open(file_path, "wb"):
            pass  # create empty file
        node = JuiceFSFileNode(cast("JuiceFSFileSystem", self.fs), file_path)
        self.fs._notify_change(node, "create")
        return node

    def insert_dir(self, name: str) -> "JuiceFSDirNode":
        dir_path = os.path.join(self.path if self.path != "/" else "", name)
        if self.fs.client.exists(dir_path):
            raise FileExistsError(dir_path)
        self.fs.client.makedirs(dir_path)
        node = JuiceFSDirNode(cast("JuiceFSFileSystem", self.fs), dir_path)
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
    def _notify_change(self, node: FileSystemNode, change_type: CHANGE_TYPE):
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
