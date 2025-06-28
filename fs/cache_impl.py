"""
缓存文件系统：用 OSFileSystem 做本地缓存，以 JuiceFSFileSystem 为后端。
读操作 → 先查本地缓存；未命中则从 JuiceFS 读取并写入缓存
写操作 → 先写本地缓存，再写远端 JuiceFS（write-through）
"""

from __future__ import annotations

import io
import os
import time
import threading
import tempfile
from contextlib import contextmanager
from typing import Optional, List


from .osfs_impl import OSFileSystem, OSFileSystemNode
from .jfs_impl import JuiceFSFileSystem, JuiceFSFileSystemNode
from . import IOSYSFileSystem, FileSystemNode

# chunk size for streaming reads
_CHUNK = 65536


# --------------------------------------------------------------------------- #
# 主文件系统
# --------------------------------------------------------------------------- #
class CacheFileSystem(IOSYSFileSystem):
    """
    组合模式（而非多重继承）包装 OSFileSystem + JuiceFSFileSystem。
    """

    def __init__(self, cache_fs: OSFileSystem, backend_fs: JuiceFSFileSystem) -> None:
        super().__init__()
        self.cache_fs = cache_fs  # 本地缓存
        self.backend_fs = backend_fs  # 远端存储

    # ------------ 基础工具 ------------
    @staticmethod
    def _norm(path: str) -> str:
        """标准化：以 / 开头，去掉多余尾斜杠（根目录除外）"""
        if not path.startswith("/"):
            path = "/" + path
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        return path

    # ------------ IOSYSFileSystem API ------------
    def is_running(self) -> bool:
        return self.cache_fs.is_running() and self.backend_fs.is_running()

    def get_node(self, path: str) -> Optional["CacheFileSystemNode"]:
        path = self._norm(path)

        # 已在本地缓存 → 直接返回
        if self.cache_fs.get_node(path):
            return CacheFileSystemNode(self, path)

        # 本地无 → 看远端
        backend_node = self.backend_fs.get_node(path)
        if backend_node is None:
            return None  # 远端也不存在

        # 远端是目录：**只返回一个包装节点**，不建任何本地目录
        if backend_node._meta.get("type") == "directory":
            return CacheFileSystemNode(self, path)

        # 远端是文件：把文件内容拉回本地
        data = backend_node.read()  # 读远端文件
        # 让 OSFS 自己确保父目录存在并写入；不会多余地建目录
        self.cache_fs.write_file(path, data)  # OSFS 内部 already handles makedirs
        return CacheFileSystemNode(self, path)


# --------------------------------------------------------------------------- #
# 节点封装
# --------------------------------------------------------------------------- #
class CacheFileSystemNode(FileSystemNode):
    """
    单个路径对应的节点，内部委托 cache_fs / backend_fs 的节点实现具体 IO。
    """

    fs: "CacheFileSystem"

    # ---------- 内部委托 ----------
    @property
    def _cache_node(self) -> FileSystemNode:
        node = self.fs.cache_fs.get_node(self.path)
        if node is None:
            # 如果缓存文件尚未创建，实例化一个占位节点
            node = OSFileSystemNode(self.fs.cache_fs, self.path)
        return node

    @property
    def _backend_node(self) -> FileSystemNode:
        node = self.fs.backend_fs.get_node(self.path)
        # 如果文件尚未创建，实例化一个占位节点
        if node is None:
            node = JuiceFSFileSystemNode(self.fs.backend_fs, self.path)
        return node

    # ------------------------------------------------------------
    # 新增一个简单的文件级进程内锁，防止并发读时重复回源
    # ------------------------------------------------------------
    _locks: dict[str, threading.Lock] = {}

    @contextmanager
    def _file_lock(self, path: str):
        lock = self._locks.setdefault(path, threading.Lock())
        lock.acquire()
        try:
            yield
        finally:
            lock.release()

    # ------------------------------------------------------------
    # read_stream —— 缓存有直接读；无缓存则边流式写边返回
    # ------------------------------------------------------------
    def read_stream(self) -> io.BytesIO:
        """
        1) 若缓存文件已存在 → 直接 return open(local_path, "rb")
        2) 若不存在 → 与其他并发线程协商，只让 1 个线程真正回源；
           2-a) 用远端流按块写入临时文件 (.part)，
           2-b) 写完后原子 rename → 正式缓存文件，
           2-c) 再打开缓存文件并 return。
        整个过程对调用方透明，且不会把全文件载入内存。
        """
        if self._cache_node:  # 已缓存
            return self._cache_node.read_stream()

        # -------- 缓存未命中，进入加锁区，避免并发重复拉取 --------
        with self._file_lock(self.path):
            # 第二次进入时可能已有其他线程写好缓存，因此再检查一遍
            if self.fs.cache_fs.get_node(self.path):
                return self._cache_node.read_stream()

            backend_node = self.fs.backend_fs.get_node(self.path)
            if backend_node is None:
                raise FileNotFoundError(self.path)
            if backend_node._meta.get("type") == "directory":
                raise IsADirectoryError(self.path)

            # 准备本地目录并创建临时文件
            # 获取缓存节点的实际文件路径
            local_path = self._cache_node.get_real_path()
            local_dir = os.path.dirname(local_path)
            os.makedirs(local_dir, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(dir=local_dir, suffix=".part")
            os.close(fd)

            try:
                # --- 流式复制 ---
                with backend_node.read_stream() as src, open(tmp_path, "wb") as dst:
                    for chunk in iter(lambda: src.read(_CHUNK), b""):
                        dst.write(chunk)

                # --- 原子 rename 成正式文件名 ---
                final_path = self.fs.cache_fs.get_real_path(self.path)
                os.replace(tmp_path, final_path)

                # 更新本地节点元数据、触发事件
                self._cache_node.update_meta(
                    type="file",
                    size=os.path.getsize(final_path),
                    modified_at=int(time.time()),
                )
                self.fs.fire_event("update", self)
            finally:
                # 若发生异常确保临时文件被清理
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        # 最终以缓存文件流返回
        return self._cache_node.read_stream()

    def write(self, content: bytes):
        # 1) 写缓存
        self._cache_node.write(content)
        # 2) 写远端
        self._backend_node.write(content)
        # 3) 更新元数据 + 事件
        self.update_meta(type="file", modified_at=int(time.time()))
        self.fs.fire_event("update", self)

    # ------- 维护操作 -------
    def remove(self):
        # 先删远端，后删本地
        if self.fs.backend_fs.get_node(self.path):
            self._backend_node.remove()
        if self.fs.cache_fs.get_node(self.path):
            self._cache_node.remove()
        self.fs.fire_event("delete", self)

    def move_to(self, target_path: str):
        target_path = self.fs._norm(target_path)
        # 后端
        if self.fs.backend_fs.get_node(self.path):
            self._backend_node.move_to(target_path)
        # 缓存
        if self.fs.cache_fs.get_node(self.path):
            self._cache_node.move_to(target_path)
        # 更新自身
        self.path = target_path
        self.fs.fire_event("update", self)

    # ------- 目录相关 -------
    def children(self) -> List["CacheFileSystemNode"]:
        # 合并本地与远端子节点名称
        names = set()
        for system in (self.fs.cache_fs, self.fs.backend_fs):
            n = system.get_node(self.path)
            if n:
                for child in n.children():
                    names.add(child.path)
        return [CacheFileSystemNode(self.fs, p) for p in names]

    def _sync_metadata(self):
        return super()._sync_metadata()

    def create_child(self, name: str) -> "CacheFileSystemNode":
        """
        创建子节点，先在缓存中创建，再在远端创建。
        """
        child_path = self.fs._norm(os.path.join(self.path, name))
        # 1) 在缓存中创建
        self._cache_node.create_child(name)
        # 2) 在远端创建
        self._backend_node.create_child(name)
        return CacheFileSystemNode(self.fs, child_path)

    def makedir(self):
        self._cache_node.makedir()
        self._backend_node.makedir()

    def parent(self) -> Optional["CacheFileSystemNode"]:
        parent_path = os.path.dirname(self.path) or "/"
        return self.fs.get_node(parent_path) if parent_path != "/" else None
