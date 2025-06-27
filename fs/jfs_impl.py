from __future__ import annotations

import io
import os
from typing import Union
import time
import json
import juicefs  # type: ignore

from . import (
    FileSystemNode,
    IOSYSFileSystem,
)  # Assuming DirNode is defined elsewhere
from utils.logger import IOSYSLogger


class JuiceFSFileSystemNode(FileSystemNode):
    fs: "JuiceFSFileSystem"

    def read_stream(self) -> io.BytesIO:
        if self.meta.get("type") == "directory":
            raise IsADirectoryError(f"Cannot read a directory: {self.path}")
        # 对于文件或嵌入节点，从JuiceFS读取内容
        content_bytes = self.fs.client.read_file(self.path)
        return io.BytesIO(content_bytes)

    def write(self, content: bytes):
        node_type = self.meta.get("type")
        if node_type == "directory":
            raise IsADirectoryError(f"Cannot write to a directory: {self.path}")
        # 如果是新建的占位节点或嵌入节点，可能需要在JuiceFS创建文件
        self.fs.client.write_file(self.path, content)
        # 更新元数据类型为文件，记录修改时间
        self.update_meta(type="file", modified_at=int(time.time()))
        self.fs.invoke_on_change(self, "update")

    def makedir(self):
        node_type = self.meta.get("type")
        if node_type and node_type != "directory":
            # 已存在且不是目录，不能转换为目录
            raise ValueError(
                f"Cannot make directory at {self.path}, node is {node_type}"
            )
        self.fs.client.make_dir(self.path)  # 在JuiceFS创建目录
        # 设置元数据为目录类型
        self.update_meta(
            type="directory", created_at=int(time.time()), modified_at=int(time.time())
        )
        self.fs.invoke_on_change(self, "create")

    def remove(self):
        node_type = self.meta.get("type")
        if node_type == "embedded":
            raise ValueError("Cannot remove embedded content directly")
        # 根据类型删除
        if node_type == "directory":
            self.fs.client.remove_dir(self.path)  # 可能需要确保目录为空
        else:
            self.fs.client.remove_file(self.path)
        # 删除元数据文件
        meta_path = self.fs._get_meta_path(self.path)
        self.fs.client.remove_file(meta_path + "/.meta.json")
        self.fs.invoke_on_change(self, "delete")

    def parent(self) -> Union["JuiceFSFileSystemNode", None]:
        """Return the parent directory node."""
        if self.path == "/":
            return None
        parent_path = os.path.dirname(self.path.rstrip("/"))
        return JuiceFSFileSystemNode(self.fs, parent_path)

    def children(self) -> list[FileSystemNode]:
        node_type = self.meta.get("type")
        children_nodes = []
        if node_type == "directory":
            for name in self.fs.client.list_dir(self.path):
                child_path = f"{self.path}/{name}"
                child_node = self.fs.get_node(child_path)
                if child_node:
                    children_nodes.append(child_node)
        elif node_type == "file":
            # 列出嵌入内容
            meta_dir = self.fs._get_meta_path(self.path)
            for name in self.fs.client.list_dir(meta_dir):
                child_path = f"{self.path}/{name}"
                child_node = self.fs.get_node(child_path)
                if child_node:
                    children_nodes.append(child_node)
        return children_nodes

    def create_child(self, name: str) -> "JuiceFSFileSystemNode":
        # 禁止在嵌入节点上再创建子节点，避免无限嵌套
        if self.meta.get("type") == "embedded":
            raise ValueError("Cannot create child in an embedded file node.")
        # 生成子节点路径
        child_path = self.path.rstrip("/") + "/" + name
        node = JuiceFSFileSystemNode(self.fs, child_path)
        # 如果当前节点是文件，则子节点标记为嵌入类型
        if self.meta.get("type") == "file":
            node.update_meta(
                type="embedded",
                created_at=int(time.time()),
                modified_at=int(time.time()),
            )
        else:
            # 父为目录，新子节点暂不赋类型，等待实际操作决定
            node.update_meta(created_at=int(time.time()), modified_at=int(time.time()))
        return node

    def _sync_metadata(self):
        # 将元数据写入JuiceFS的元数据存储，比如.path/.meta.json
        meta_json_path = self.fs._get_meta_path(self.path) + "/.meta.json"
        old_meta = {}
        if self.fs.client.exists(meta_json_path):
            old_meta = json.loads(self.fs.client.read_file(meta_json_path).decode())
        # 合并旧meta和新meta（新meta优先）
        merged_meta = {
            **old_meta,
            **{k: v for k, v in self.meta.items() if v is not None},
        }
        self.meta = merged_meta  # 更新当前内存中的meta
        self.fs.client.write_file(
            meta_json_path, json.dumps(merged_meta, indent=2).encode()
        )
        # 不调用invoke_on_change这里，以免重复，多数情况下调用update_meta时会触发


class JuiceFSFileSystem(IOSYSFileSystem):
    def __init__(self):
        super().__init__()
        self.logger = IOSYSLogger("JuiceFS")

        # Spawn side‑car service if needed (e.g., HTTP API to remote JFS).
        # self.service = JuiceFSService()
        # self.service.start()

        # Initialise client – supports either native conf or explicit meta URL.
        name = os.getenv("JFS_NAME")
        meta = os.getenv("JFS_META_URL")
        token = os.getenv("JFS_TOKEN")
        access_key = os.getenv("JFS_ACCESS_KEY")
        secret_key = os.getenv("JFS_SECRET_KEY")

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
        # 查询JuiceFS元数据或文件状态
        if self.client.is_file(path):
            node = JuiceFSFileSystemNode(self, path)
            node.update_meta(type="file")
            return node
        if self.client.is_dir(path):
            node = JuiceFSFileSystemNode(self, path)
            node.update_meta(type="directory")
            return node
        # 检查是否存在元数据目录表示嵌入文件
        meta_path = self._get_meta_path(path)
        if self.client.is_dir(meta_path):
            node = JuiceFSFileSystemNode(self, path)
            node.update_meta(type="embedded")
            return node
        return None  # 路径不存在

    def _get_meta_path(self, path: str) -> str:
        # 类似OSFS，把虚拟路径转换为元数据实际路径
        if path == "/":
            return "/.meta"  # 假设JuiceFS也采用类似隐藏目录
        return f"/.meta{path}"
