import unittest
from jfs import new_fs, FileSystemNode
import asyncio

class TestIOSYSFileSystem(unittest.TestCase):
    def setUp(self):
        """Initialize the file system."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.fs = new_fs()  # Initialize the file system using new_fs()

    def test_root_exists(self):
        """Test if the root directory exists."""
        root_node = self.fs.get_root()
        self.assertIsInstance(root_node, FileSystemNode, "Root node should exist.")
        self.assertEqual(root_node.path, "/", "Root path should be '/'.")

    def test_create_and_read_file(self):
        """Test creating and reading a file."""
        file_path = "/test_file.txt"
        content = b"Hello, IOSYS!"

        # Write file
        file_node = self.fs.write_file(file_path, content)
        self.assertIsInstance(file_node, FileSystemNode, "File node should be created.")
        self.assertEqual(file_node.path, file_path, "File path should match.")

        # Read file
        read_content = self.fs.read(file_path)
        self.assertEqual(read_content, content, "File content should match.")

    def test_create_and_remove_directory(self):
        """Test creating and removing a directory."""
        dir_path = "/test_dir"

        # Create directory
        dir_node = self.fs.ensure_directory(dir_path)
        self.assertIsInstance(
            dir_node, FileSystemNode, "Directory node should be created."
        )
        self.assertEqual(dir_node.path, dir_path, "Directory path should match.")

        # Remove directory
        self.fs.remove(dir_path)
        with self.assertRaises(FileNotFoundError):
            self.fs.get_node(dir_path)

    def test_file_not_found(self):
        """Test accessing a non-existent file."""
        with self.assertRaises(FileNotFoundError):
            self.fs.read("/non_existent_file.txt")

    def test_directory_not_found(self):
        """Test accessing a non-existent directory."""
        with self.assertRaises(FileNotFoundError):
            self.fs.get_node("/non_existent_dir")

    def test_normalize_path(self):
        """Test path normalization."""
        normalized_path = self.fs._normalize_path("///test//path/")
        self.assertEqual(normalized_path, "/test/path", "Path should be normalized.")


if __name__ == "__main__":
    unittest.main()
