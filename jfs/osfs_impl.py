import io
import os
from . import FileNode, DirNode, IOSYSFileSystem


class OSFileNode(FileNode):
    def __init__(self, fs: "OSFileSystem", id: str):
        self.fs = fs
        self.type = "file"
        self.id = id
        self.name = os.path.basename(id.rstrip("/"))
        self.meta = {}

    def read_stream(self) -> io.BytesIO:
        """Open the file and read bytes"""
        real_path = self.fs._get_real_path(self.id)
        if not os.path.exists(real_path):
            raise FileNotFoundError(f"File {self.id} not found.")
        if os.path.isdir(real_path):
            raise IsADirectoryError(f"{self.id} is a directory.")
        return open(real_path, "rb")

    def write(self, content: bytes):
        """Write bytes to file (overwrite)"""
        real_path = self.fs._get_real_path(self.id)
        if not os.path.exists(real_path):
            raise FileNotFoundError(f"File {self.id} not found.")
        if os.path.isdir(real_path):
            raise IsADirectoryError(f"{self.id} is a directory.")
        with open(real_path, "wb") as f:
            f.write(content)
        self.fs.call_file_update(self)

    def remove(self):
        """Remove the file"""
        real_path = self.fs._get_real_path(self.id)
        if not os.path.exists(real_path):
            raise FileNotFoundError(f"File {self.id} not found.")
        if os.path.isdir(real_path):
            raise IsADirectoryError(f"{self.id} is a directory.")
        os.remove(real_path)
        self.fs.call_file_delete(self)

    def parent(self) -> "OSDirNode":
        parent_id = os.path.dirname(self.id.rstrip("/"))
        if parent_id == "":
            parent_id = "/"
        return OSDirNode(self.fs, parent_id)


class OSDirNode(DirNode):
    def __init__(self, fs: "OSFileSystem", id: str):
        self.fs = fs
        self.type = "dir"
        self.id = id
        self.name = os.path.basename(id.rstrip("/"))
        self.meta = {}

    def insert_file(self, name: str) -> FileNode:
        """Create a new file in this directory"""
        file_path = os.path.join(self.id, name).replace("\\", "/")
        real_path = self.fs._get_real_path(file_path)
        if os.path.exists(real_path):
            raise FileExistsError(f"File {file_path} already exists.")

        # Create empty file
        with open(real_path, "wb") as _:
            pass

        node = OSFileNode(self.fs, file_path)
        self.fs.call_file_update(node)
        return node

    def insert_dir(self, name: str) -> "OSDirNode":
        """Create a new directory in this directory"""
        dir_path = os.path.join(self.id, name).replace("\\", "/")
        real_path = self.fs._get_real_path(dir_path)
        if os.path.exists(real_path):
            raise FileExistsError(f"Directory {dir_path} already exists.")

        os.makedirs(real_path)
        node = OSDirNode(self.fs, dir_path)
        self.fs.call_dir_update(node)
        return node

    def remove(self):
        """Remove the directory"""
        real_path = self.fs._get_real_path(self.id)
        if not os.path.exists(real_path):
            raise FileNotFoundError(f"Directory {self.id} not found.")
        if not os.path.isdir(real_path):
            raise NotADirectoryError(f"{self.id} is not a directory.")
        os.rmdir(real_path)
        self.fs.call_dir_delete(self)

    def parent(self) -> "OSDirNode":
        parent_id = os.path.dirname(self.id.rstrip("/"))
        if parent_id == "":
            parent_id = "/"
        return OSDirNode(self.fs, parent_id)

    def children(self) -> list[FileNode]:
        real_path = self.fs._get_real_path(self.id)
        if not os.path.exists(real_path) or not os.path.isdir(real_path):
            return []

        children = []
        for item in os.listdir(real_path):
            item_path = os.path.join(self.id, item).replace("\\", "/")
            real_item_path = self.fs._get_real_path(item_path)
            if os.path.isfile(real_item_path):
                children.append(OSFileNode(self.fs, item_path))
            elif os.path.isdir(real_item_path):
                children.append(OSDirNode(self.fs, item_path))
        return children


class OSFileSystem(IOSYSFileSystem):
    def __init__(self, root_path: str):
        super().__init__()
        self.root_path = os.path.abspath(root_path).replace("\\", "/")
        os.makedirs(self.root_path, exist_ok=True)

    def _get_real_path(self, virtual_path: str) -> str:
        """Convert virtual path to real path within root_path and validate it"""
        # Normalize the virtual path
        virtual_path = virtual_path.strip("/").replace("\\", "/")

        # Join with root path
        real_path = os.path.join(self.root_path, virtual_path).replace("\\", "/")
        real_path = os.path.abspath(real_path).replace("\\", "/")

        # Security check: ensure the real path is within root_path
        if not real_path.startswith(self.root_path):
            raise PermissionError(
                f"Access denied: path {virtual_path} is outside root directory"
            )

        return real_path

    def is_running(self) -> bool:
        return True

    def get_node(self, id: str) -> FileNode | DirNode | None:
        if not self.exists(id):
            return None

        real_path = self._get_real_path(id)
        if os.path.isdir(real_path):
            return OSDirNode(self, id)
        elif os.path.isfile(real_path):
            return OSFileNode(self, id)
        return None

    def exists(self, id: str) -> bool:
        try:
            real_path = self._get_real_path(id)
            return os.path.exists(real_path)
        except PermissionError:
            return False
