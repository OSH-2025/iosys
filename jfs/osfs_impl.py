import os
from . import FileNode, DirNode, IOSYSFileSystem


class OSFileNode(FileNode):
    def __init__(self, fs: "OSFileSystem", id: str):
        self.fs = fs
        self.type = "file"
        self.id = id
        self.name = os.path.basename(id.rstrip("/"))
        self.meta = {}

    def read(self) -> bytes:
        """Open the file and read bytes"""
        if not os.path.exists(self.id):
            raise FileNotFoundError(f"File {self.id} not found.")
        if os.path.isdir(self.id):
            raise IsADirectoryError(f"{self.id} is a directory.")
        with open(self.id, "rb") as f:
            return f.read()

    def write(self, content: bytes):
        """Write bytes to file (overwrite)"""
        if not os.path.exists(self.id):
            raise FileNotFoundError(f"File {self.id} not found.")
        if os.path.isdir(self.id):
            raise IsADirectoryError(f"{self.id} is a directory.")
        with open(self.id, "wb") as f:
            f.write(content)
        self.fs.call_file_update(self)

    def remove(self):
        """Remove the file"""
        if not os.path.exists(self.id):
            raise FileNotFoundError(f"File {self.id} not found.")
        if os.path.isdir(self.id):
            raise IsADirectoryError(f"{self.id} is a directory.")
        os.remove(self.id)
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

    def insert(self, node: FileNode | DirNode):
        # Implementation for creating files/dirs
        pass

    def remove(self):
        """Remove the directory"""
        if not os.path.exists(self.id):
            raise FileNotFoundError(f"Directory {self.id} not found.")
        if not os.path.isdir(self.id):
            raise NotADirectoryError(f"{self.id} is not a directory.")
        os.rmdir(self.id)
        self.fs.call_dir_delete(self)

    def parent(self) -> "OSDirNode":
        parent_id = os.path.dirname(self.id.rstrip("/"))
        if parent_id == "":
            parent_id = "/"
        return OSDirNode(self.fs, parent_id)

    def children(self) -> list[FileNode]:
        if not os.path.exists(self.id) or not os.path.isdir(self.id):
            return []

        children = []
        for item in os.listdir(self.id):
            item_path = os.path.join(self.id, item)
            if os.path.isfile(item_path):
                children.append(OSFileNode(self.fs, item_path))
            elif os.path.isdir(item_path):
                children.append(OSDirNode(self.fs, item_path))
        return children


class OSFileSystem(IOSYSFileSystem):
    def __init__(self, root_path: str = "/"):
        super().__init__()
        self.root_path = root_path

    def get_node(self, id: str) -> FileNode | DirNode | None:
        if not self.exists(id):
            return None

        if os.path.isdir(id):
            return OSDirNode(self, id)
        elif os.path.isfile(id):
            return OSFileNode(self, id)
        return None

    def exists(self, id: str) -> bool:
        return os.path.exists(id)
