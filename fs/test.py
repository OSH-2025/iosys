import asyncio
from fs import new_fs, FileSystemNode


def main():
    # Initialize the file system
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    fs = new_fs()
    loop.run_until_complete(run_tests(fs))


async def run_tests(fs):
    # Test if the root directory exists
    print("Testing root directory existence...")
    root_node = fs.get_root()
    assert isinstance(root_node, FileSystemNode), "Root node should exist."
    assert root_node.path == "/", "Root path should be '/'."
    print("Root directory test passed.")

    # Test creating and reading a file
    print("Testing file creation and reading...")
    file_path = "/test_file.txt"
    content = b"Hello, IOSYS!"
    file_node = fs.write_file(file_path, content)
    assert isinstance(file_node, FileSystemNode), "File node should be created."
    assert file_node.path == file_path, "File path should match."
    read_content = fs.read(file_path)
    assert read_content == content, "File content should match."
    print("File creation and reading test passed.")

    # Test creating and removing a directory
    print("Testing directory creation and removal...")
    dir_path = "/test_dir"
    dir_node = fs.ensure_directory(dir_path)
    assert isinstance(dir_node, FileSystemNode), "Directory node should be created."
    assert dir_node.path == dir_path, "Directory path should match."
    fs.remove(dir_path)
    try:
        fs.get_node(dir_path)
        assert False, "Directory should not exist after removal."
    except FileNotFoundError:
        print("Directory creation and removal test passed.")

    # Test accessing a non-existent file
    print("Testing non-existent file access...")
    try:
        fs.read("/non_existent_file.txt")
        assert False, "Accessing a non-existent file should raise FileNotFoundError."
    except FileNotFoundError:
        print("Non-existent file access test passed.")

    # Test accessing a non-existent directory
    print("Testing non-existent directory access...")
    try:
        fs.get_node("/non_existent_dir")
        assert False, (
            "Accessing a non-existent directory should raise FileNotFoundError."
        )
    except FileNotFoundError:
        print("Non-existent directory access test passed.")

    # Test path normalization
    print("Testing path normalization...")
    normalized_path = fs.normalize_path("///test//path/")
    assert normalized_path == "/test/path", "Path should be normalized."
    print("Path normalization test passed.")


if __name__ == "__main__":
    main()
