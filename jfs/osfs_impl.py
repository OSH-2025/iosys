import io
import json
import time
import os
from typing import Union
from . import FileSystemNode, IOSYSFileSystem


class OSFileSystemNode(FileSystemNode):
    fs: "OSFileSystem"

    def read_stream(self) -> io.BytesIO:
        """Open the file and read bytes"""
        if self.meta.get("type") == "embedded":
            real_path = self.fs._get_embedded_path(self.path)
            with open(real_path, "rb") as f:
                return io.BytesIO(f.read())
        real_path = self.fs._get_real_path(self.path)
        if self.meta.get("type") == "directory":
            raise IsADirectoryError(f"Cannot read a directory as a file: {self.path}")
        if not os.path.exists(real_path):
            return io.BytesIO()
        with open(real_path, "rb") as f:
            return io.BytesIO(f.read())

    def write(self, content: bytes):
        """Write bytes to file (overwrite)"""
        if self.meta.get("type") == "embedded":
            raise ValueError("Cannot write to an embedded file directly.")
        real_path = self.fs._get_real_path(self.path)
        if self.meta.get("type") == "directory":
            raise IsADirectoryError(
                f"Cannot write to a directory as a file: {self.path}"
            )
        with open(real_path, "wb") as f:
            f.write(content)
        self.update_meta(
            type="file",
            modified_at=int(time.time()),
        )
        self.fs.invoke_on_change(self, "update")

    def makedir(self):
        """Create a directory node"""
        node_type = self.meta.get("type")
        if node_type and not node_type == "directory":
            raise ValueError(
                f"Wrong node type for makedir at {self.path}, got '{node_type}'"
            )
        real_path = self.fs._get_real_path(self.path)
        os.makedirs(real_path, exist_ok=True)
        self.update_meta(
            type="directory",
            created_at=int(time.time()),
            modified_at=int(time.time()),
        )
        self.fs.invoke_on_change(self, "create")

    def remove(self):
        """Remove the file"""
        if self.meta.get("type") == "embedded":
            raise ValueError("Cannot remove an embedded file directly.")
        real_path = self.fs._get_real_path(self.path)
        if os.path.exists(real_path):
            os.remove(real_path)
        meta_path = self.fs._get_meta_path(self.path)
        if os.path.exists(meta_path):
            os.remove(meta_path)
        self.fs.invoke_on_change(self, "delete")

    def parent(self) -> Union["OSFileSystemNode", None]:
        if self.path == "/":
            return None
        return self.fs.get_node(os.path.dirname(self.path))

    def children(self) -> list[FileSystemNode]:
        real_path = self.fs._get_real_path(self.path)
        if not os.path.exists(real_path):
            return []

        children = []
        for item in os.listdir(real_path):
            if item.startswith("."):
                continue
            item_path = f"{self.path}/{item}"
            children.append(self.fs.get_node(item_path))
        return children

    def create_child(self, name: str) -> "OSFileSystemNode":
        if self.meta.get("embedded") == "embedded":
            raise ValueError("Cannot insert node into an embedded file.")
        if self.path == "/":
            path = f"/{name}"
        else:
            path = f"{self.path}/{name}"
        node = OSFileSystemNode(self.fs, path)
        node.update_meta(
            type="embedded" if self.meta.get("type") == "file" else None,
            created_at=int(time.time()),
            modified_at=int(time.time()),
        )
        return node

    def _sync_metadata(self):
        if self.path == "/":
            return
        meta_dir = self.fs._get_meta_path(self.path)
        os.makedirs(meta_dir, exist_ok=True)
        meta_json = os.path.join(meta_dir, ".meta.json")
        if os.path.exists(meta_json):
            with open(meta_json, "r") as f:
                old_meta = f.read()
        else:
            old_meta = None
        if old_meta and old_meta != "{}":
            self.meta = {
                **json.loads(old_meta),
                **{k: v for k, v in self.meta.items() if v is not None},
            }
            self.fs.invoke_on_change(self, "metadata")
        with open(meta_json, "w") as f:
            f.write(json.dumps(self.meta, indent=2))


class OSFileSystem(IOSYSFileSystem):
    def __init__(self, root_path: str):
        super().__init__()
        self.root_path = os.path.abspath(root_path).replace("\\", "/")
        os.makedirs(self.root_path, exist_ok=True)

    def is_running(self) -> bool:
        return True

    def get_node(self, path: str) -> OSFileSystemNode | None:
        path = self._normalize_path(path)
        real_path = self._get_real_path(path)
        # Case 1: The file just exists
        if os.path.exists(real_path):
            node = OSFileSystemNode(self, path)
            node.update_meta(type="file" if os.path.isfile(real_path) else "directory")
            return node
        # Case 2: The metadata exists, but the file hasn't been created yet or is a embedded file
        if path != "/":
            meta_path = self._get_meta_path(path)
            if os.path.isdir(meta_path):
                node = OSFileSystemNode(self, path)
                node.update_meta(type="embedded")
                return node

    def _get_real_path(self, virtual_path: str) -> str:
        """Convert virtual path to real path within root_path and validate it"""
        if not virtual_path.startswith("/") or (
            not virtual_path == "/" and virtual_path.endswith("/")
        ):
            raise ValueError(f"Invalid virtual path: {virtual_path}")
        virtual_path = virtual_path[1:]  # Remove leading slash

        # Join with root path
        real_path = os.path.join(self.root_path, virtual_path)
        real_path = os.path.abspath(real_path).replace("\\", "/")

        # Security check: ensure the real path is within root_path
        if not real_path.startswith(self.root_path):
            raise PermissionError(
                f"Access denied: path {real_path} is outside root directory {self.root_path}"
            )

        return real_path

    def _get_meta_path(self, path: str) -> str:
        return self._get_real_path(f"/.meta{path}")

    def _get_embedded_path(self, path: str) -> str:
        return self._get_real_path(f"/.meta{path}/.content")
