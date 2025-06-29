from __future__ import annotations

import io
import os
from typing import Union
import time
import json
import juicefs  # type: ignore
import errno

from . import (
    FileSystemNode,
    IOSYSFileSystem,
)  # Assuming DirNode is defined elsewhere
from utils.logger import IOSYSLogger


def _now() -> int:
    """Get current time in seconds since epoch."""
    return int(time.time())


class JuiceFSFileSystemNode(FileSystemNode):
    fs: "JuiceFSFileSystem"

    def read_stream(self) -> io.BytesIO:
        if self._meta.get("type") == "embedded":
            # 对于嵌入节点，直接从JuiceFS读取内容
            parent = self.parent()
            assert parent
            content_bytes = self.fs.client.getxattr(
                parent.path, "user.iosys.embedded.content." + self.name
            )
            if content_bytes is None:
                return io.BytesIO()
            return io.BytesIO(content_bytes)
        if self._meta.get("type") == "directory":
            raise IsADirectoryError(f"Cannot read a directory: {self.path}")
        # 对于文件或嵌入节点，从JuiceFS读取内容
        filecode = self.fs.client.open(self.path, "rb")
        try:
            raw = filecode.io.read()
            # ensure we always have bytes for BytesIO
            content_bytes = raw.encode() if isinstance(raw, str) else raw
        finally:
            filecode.close()

        return io.BytesIO(content_bytes)

    def write(self, content: bytes):
        if self._meta.get("type") == "embedded":
            parent = self.parent()
            assert parent
            self.fs.client.setxattr(
                parent.path,
                "user.iosys.embedded.content." + self.name,
                content,
            )
            return
        node_type = self._meta.get("type")
        if node_type == "directory":
            raise IsADirectoryError(f"Cannot write to a directory: {self.path}")
        # 如果是新建的占位节点或嵌入节点，可能需要在JuiceFS创建文件
        filecode = self.fs.client.open(self.path, "wb")
        try:
            filecode.write(content)
        finally:
            filecode.close()
        # 更新元数据类型为文件，记录修改时间
        self.update_meta(type="file", modified_at=_now())
        self.fs.fire_event("update", self)

    def makedir(self):
        node_type = self._meta.get("type")
        if node_type and node_type != "directory":
            # 已存在且不是目录，不能转换为目录
            raise ValueError(
                f"Cannot make directory at {self.path}, node is {node_type}"
            )
        self.fs.client.makedirs(self.path, exist_ok=True)  # 在JuiceFS创建目录
        # 设置元数据为目录类型
        self.update_meta(type="directory", created_at=_now(), modified_at=_now())
        self.fs.fire_event("create", self)

    """
    def remove(self):
        node_type = self._meta.get("type")
        if node_type == "embedded":
            raise ValueError("Cannot remove embedded content directly")
        # 根据类型删除
        #print(self.fs.client.listdir(self.path))  # 确保目录存在
        self.fs.client.remove(self.path)  # 可能需要确保目录为空
        self.fs.fire_event("delete", self)
    """

    def remove(self):
        """递归删除；保证目录在调用 jfs_delete 之前已空。"""

        node_type = self._meta.get("type")
        if node_type == "embedded":
            raise ValueError("Cannot remove embedded content directly")

        # 若自己是目录，先删光子节点
        if node_type == "directory":
            for name in self.fs.client.listdir(self.path):
                child_path = f"{self.path.rstrip('/')}/{name}"
                child = JuiceFSFileSystemNode(self.fs, child_path)
                child._sync_metadata()
                child.remove()

        # 删掉自己（目录此时已空 / 文件直接删）
        self.fs.client.remove(self.path)
        self.fs.fire_event("delete", self)

    def parent(self) -> Union["JuiceFSFileSystemNode", None]:
        """Return the parent directory node."""
        if self.path == "/":
            return None
        return self.fs.get_node(os.path.dirname(self.path.rstrip("/")))

    def children(self) -> list[FileSystemNode]:
        if self._meta.get("type") != "directory":
            return []
        try:
            names = self.fs.client.listdir(self.path)
        except Exception:
            return []
        result: list[FileSystemNode] = []
        for name in names:
            child = self.fs.get_node(os.path.join(self.path, name))
            if child:
                result.append(child)
        return result

    def create_child(self, name: str) -> "JuiceFSFileSystemNode":
        # 禁止在嵌入节点上再创建子节点，避免无限嵌套
        if self._meta.get("type") == "embedded":
            raise ValueError("Cannot create child in an embedded file node.")
        # 生成子节点路径
        child_path = self.path.rstrip("/") + "/" + name
        node = JuiceFSFileSystemNode(self.fs, child_path)
        # 如果当前节点是文件，则子节点标记为嵌入类型
        if self._meta.get("type") == "file":
            node.update_meta(
                type="embedded",
                created_at=_now(),
                modified_at=_now(),
            )
        else:
            node._meta["created_at"] = _now()
            node._meta["modified_at"] = _now()
            # 父为目录，新子节点暂不赋类型，等待实际操作决定
            # node.update_meta(created_at=_now(), modified_at=_now())
            # self.fs.client.open(child_path, "wb").close()
        return node

    def move_to(self, target_path: str) -> None:
        """Move this node to a new path."""
        # rename in JuiceFS
        target_path = self.fs.normalize_path(target_path)
        parent_dir = os.path.dirname(target_path.rstrip("/"))
        if parent_dir:
            self.fs.ensure_directory(parent_dir)
        self.fs.client.rename(self.path, target_path)
        # update local path and metadata
        self.path = target_path
        self.update_meta(modified_at=_now())
        self.fs.fire_event("update", self)

    def _sync_metadata(self) -> None:
        """Reload metadata from JuiceFS xattrs."""

        if self._meta.get("type") == "embedded":
            parent = self.parent()
            assert parent
            meta_path = parent.path
            meta_name = "user.iosys.embedded.meta." + self.name
        else:
            meta_path = self.path
            meta_name = "user.iosys.meta"

        raw = None
        if self.fs.client.exists(meta_path):
            try:
                raw = self.fs.client.getxattr(meta_path, meta_name)
            except OSError as e:
                if e.errno not in (
                    errno.ENOENT,
                    errno.ENODATA,
                    getattr(errno, "ENOATTR", 61),
                ):
                    raise

        old_meta = json.loads(raw.decode()) if raw else None

        if not self._meta and old_meta:
            # If no old metadata exists, we can skip merging
            self._meta = old_meta
            return

        merged = {
            **(old_meta or {}),
            **{k: v for k, v in self._meta.items() if v is not None},
        }

        if merged != old_meta:
            self._meta = merged
            self.fs.fire_event("metadata", self)

            if not self.fs.client.exists(meta_path):
                if merged.get("type") == "directory":
                    self.fs.client.makedirs(meta_path, exist_ok=True)
                else:
                    self.fs.client.open(meta_path, "wb").close()

            self.fs.client.setxattr(
                meta_path,
                meta_name,
                json.dumps(
                    self._meta, ensure_ascii=False, separators=(",", ":")
                ).encode(),
            )


class JuiceFSFileSystem(IOSYSFileSystem):
    def __init__(self):
        super().__init__()
        self.logger = IOSYSLogger("JuiceFS")

        # Spawn side‑car service if needed (e.g., HTTP API to remote JFS).
        # self.service = JuiceFSService()
        # self.service.start()

        # Initialise client – supports either native conf or explicit meta URL.
        name = os.getenv("JFS_NAME")
        # meta = os.getenv("JFS_META_URL")
        token = os.getenv("JFS_TOKEN")
        # access_key = os.getenv("JFS_ACCESS_KEY")
        # secret_key = os.getenv("JFS_SECRET_KEY")

        kwargs = {}
        # if meta:
        #    kwargs["meta"] = meta
        if token:
            kwargs["token"] = token
        # if access_key and secret_key:
        #    kwargs["access_key"] = access_key
        #    kwargs["secret_key"] = secret_key

        self.client = juicefs.Client(name, **kwargs)  # type: ignore[arg-type]

    def is_running(self) -> bool:
        try:
            return self.client.exists("/")
        except Exception as e:
            self.logger.error(f"Failed to check JuiceFS service status: {e}")
            return False

    def get_node(self, path: str) -> JuiceFSFileSystemNode | None:
        path = self.normalize_path(path)
        if not self.client.exists(path):
            return None
        node = JuiceFSFileSystemNode(self, path)
        node._sync_metadata()  # Ensure metadata is loaded
        return node
