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
from typing import Optional, List


from .osfs_impl import OSFileSystem, OSFileSystemNode
from .jfs_impl import JuiceFSFileSystem
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

    # ------------ IOSYSFileSystem API ------------
    def is_running(self) -> bool:
        return self.cache_fs.is_running() and self.backend_fs.is_running()

    def get_node(self, path: str) -> Optional["CacheFileSystemNode"]:
        path = self.normalize_path(path)  # 确保路径标准化

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
        with backend_node.read_stream() as src:
            self.cache_fs.write_file(path, src.read())  # OSFS 自带 mkdir -p

        # 把远端的 metadata 复制到本地副本
        local_node = self.cache_fs.get_node(path)
        if local_node:
            local_node.update_meta(**backend_node._meta)
        return CacheFileSystemNode(self, path)


# --------------------------------------------------------------------------- #
# 节点封装
# --------------------------------------------------------------------------- #
class CacheFileSystemNode(FileSystemNode):
    """
    单个路径对应的节点，内部委托 cache_fs / backend_fs 的节点实现具体 IO。
    """

    fs: "CacheFileSystem"

    @property
    def _cache_node(self) -> Optional[FileSystemNode]:
        return self.fs.cache_fs.get_node(self.path)

    @property
    def _backend_node(self) -> Optional[FileSystemNode]:
        return self.fs.backend_fs.get_node(self.path)

    def _copy_meta(self, src: FileSystemNode, dst: FileSystemNode):
        """
        把 src 的 meta 全量写到 dst，并调用 dst.update_meta
        避免漏掉自定义键（JuiceFS 里 xattr；OSFS 里 side-car）
        """
        dst.update_meta(**src._meta)

    def _sync_meta_two_way(self):
        """把两端 meta 对齐为 superset，取 '最新版'(modified_at 较大者)"""
        c, b = self._cache_node, self._backend_node
        if not (c and b):
            return
        # 谁的 modified_at 大，谁覆盖谁
        if float(c._meta.get("modified_at", 0) or 0) >= float(
            b._meta.get("modified_at", 0) or 0
        ):
            self._copy_meta(c, b)
        else:
            self._copy_meta(b, c)

    # ------------------------------------------------------------
    # 新增一个简单的文件级进程内锁，防止并发读时重复回源
    # ------------------------------------------------------------
    _locks: dict[str, threading.Lock] = {}

    @classmethod
    def _lock_for(cls, path: str) -> threading.Lock:
        return cls._locks.setdefault(path, threading.Lock())

    
    def _promote_to_regular(self, os_node: FileSystemNode):
        """
        把 embedded 节点转成普通文件节点：
        1. 若存在 /.content → 原子移动到真实路径
        2. 补建父目录
        3. 写回 type="file" 到侧车
        """
        if os_node._meta.get("type") != "embedded":
            return

        real_path = self.fs.cache_fs._get_real_path(os_node.path)
        embedded_path = self.fs.cache_fs._get_embedded_path(os_node.path)

        os.makedirs(os.path.dirname(real_path), exist_ok=True)

        if os.path.exists(embedded_path):
            os.replace(embedded_path, real_path)
        os_node.update_meta(type="file")


    def read_stream(self) -> io.BytesIO:
        """
        1) 若本地缓存已存在 → 直接返回缓存文件流
        2) 否则获取文件级锁，确保只由一个线程负责下载：
           - 从 JuiceFS 以 _CHUNK 大小流式读取到临时 .part 文件
           - 下载完成后原子 rename 为正式缓存文件
           - 把远端 metadata 全量复制到本地节点
        3) 最终再次打开缓存文件并返回其流
        """
        # ---------- 1. 快速路径：缓存命中 ----------
        cache_node = self.fs.cache_fs.get_node(self.path)
        if cache_node:
            return cache_node.read_stream()

        # ---------- 2. 缓存未命中：加锁回源 ----------
        lock = self._lock_for(self.path)
        with lock:
            # 可能其他线程已完成下载；再检查一次
            cache_node = self.fs.cache_fs.get_node(self.path)
            if cache_node:
                return cache_node.read_stream()

            backend_node = self.fs.backend_fs.get_node(self.path)
            if backend_node is None:
                raise FileNotFoundError(self.path)
            if backend_node._meta.get("type") == "directory":
                raise IsADirectoryError(self.path)

            # 2-a. 预备缓存目标路径和临时文件
            real_cache_path = self.fs.cache_fs._get_real_path(self.path)
            os.makedirs(os.path.dirname(real_cache_path), exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(
                dir=os.path.dirname(real_cache_path), suffix=".part"
            )
            os.close(fd)

            try:
                # 2-b. 边读边写到临时文件
                with backend_node.read_stream() as src, open(tmp_path, "wb") as dst:
                    for chunk in iter(lambda: src.read(_CHUNK), b""):
                        dst.write(chunk)

                # 2-c. 原子替换成正式缓存文件
                os.replace(tmp_path, real_cache_path)

                # 2-d. 确保 cache_node 对象存在并同步元数据
                cache_node = self.fs.cache_fs.get_node(self.path)
                if cache_node is None:
                    cache_node = OSFileSystemNode(self.fs.cache_fs, self.path)
                cache_node.update_meta(**backend_node._meta)  # 全量复制 metadata
            finally:
                # 异常时清理临时文件
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        # ---------- 3. 返回缓存文件流 ----------
        return cache_node.read_stream()

    def write(self, content: bytes):
        cache_node   = self._cache_node   or self.fs.cache_fs.write_file(self.path, b"")
        backend_node = self._backend_node or self.fs.backend_fs.write_file(self.path, b"")

        self._promote_to_regular(cache_node)
        self._promote_to_regular(backend_node)

        cache_node.write(content)
        backend_node.write(content)

        now = int(time.time())
        cache_node.update_meta(size=len(content), modified_at=now, type="file")
        backend_node.update_meta(size=len(content), modified_at=now, type="file")

        self.update_meta(**cache_node._meta)
        self.fs.fire_event("update", self)


    # ------- 维护操作 -------
    def remove(self):
        # 先删远端，后删本地
        backend_node = self._backend_node
        if backend_node:
            backend_node.remove()
        cache_node = self._cache_node
        if cache_node:
            cache_node.remove()
        self.fs.fire_event("delete", self)

    def move_to(self, target_path: str):
        target_path = self.fs.normalize_path(target_path)
        parent_dir  = os.path.dirname(target_path) or "/"

        self.fs.cache_fs.ensure_directory(parent_dir)
        self.fs.backend_fs.ensure_directory(parent_dir)

        backend_node = self._backend_node
        if backend_node:
            backend_node.move_to(target_path)

        cache_node = self._cache_node
        if cache_node:
            cache_node.move_to(target_path)

        # 更新自身路径 & 事件
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
        return self._sync_meta_two_way()

    def create_child(self, name: str) -> "CacheFileSystemNode":
        """
        创建子节点，先在缓存中创建，再在远端创建。
        """
        child_path = self.fs.normalize_path(os.path.join(self.path, name))
        # 1) 在缓存中创建
        cache_node = self._cache_node
        if cache_node is None:
            self.fs.cache_fs.ensure_directory(self.path)  # 自动创建父目录
            cache_node = self.fs.cache_fs.get_node(self.path)
            if cache_node is None:
                raise FileNotFoundError(f"Failed to create parent directory {self.path} in cache.")
        else:
            cache_node.create_child(name)
        # 2) 在远端创建
        backend_node = self._backend_node
        if backend_node is None:
            self.fs.backend_fs.ensure_directory(self.path)  # 自动创建父目录
            backend_node = self.fs.backend_fs.get_node(self.path)
            if backend_node is None:
                raise FileNotFoundError(f"Failed to create parent directory {self.path} in backend.")
        else:
            backend_node.create_child(name)
        return CacheFileSystemNode(self.fs, child_path)

    def makedir(self):
        parent_path = os.path.dirname(self.path) or "/"
        parent = self.fs.get_node(parent_path)
        if not parent:
            raise FileNotFoundError(f"Parent directory {parent_path} not found")
        # use create_child to make a new directory in both cache and backend
        return parent.create_child(os.path.basename(self.path))

    def parent(self) -> Optional["CacheFileSystemNode"]:
        parent_path = os.path.dirname(self.path) or "/"
        return self.fs.get_node(parent_path) if parent_path != "/" else None
