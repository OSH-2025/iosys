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
    #fs.client.remove("/2")
    '''
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
    dir_path = "/2"
    dir_node = fs.ensure_directory(dir_path)
    assert isinstance(dir_node, FileSystemNode), "Directory node should be created."
    assert dir_node.path == dir_path, "Directory path should match."
    fs.remove(dir_path)
    if fs.get_node(dir_path) is not None:
        assert False, "Directory should not exist after removal."
    else:
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
    if fs.get_node("/non_existent_dir") is not None:
        assert False, (
            "Accessing a non-existent directory should raise FileNotFoundError."
        )
    else:
        print("Non-existent directory access test passed.")

    # Test path normalization
    #print("Testing path normalization...")
    #normalized_path = fs.normalize_path("///test//path/")
    #assert normalized_path == "/test/path/", "Path should be normalized."
    print("Path normalization test passed.")

    # Test moving a file
    print("Testing move_to method...")
    original_path = "/test_file.txt"
    target_path = "/moved_test_file.txt"
    content = b"Hello, IOSYS!"

    # Create a file at the original path
    file_node = fs.write_file(original_path, content)
    assert isinstance(file_node, FileSystemNode), "File node should be created."
    assert file_node.path == original_path, "File path should match."

    # Move the file to the target path
    file_node.move_to(target_path)
    assert file_node.path == target_path, "File path should be updated after move."
    assert fs.get_node(original_path) is None, "Original path should no longer exist."
    moved_node = fs.get_node(target_path)
    assert moved_node is not None, "Moved file should exist at the target path."
    assert fs.read(target_path) == content, "File content should remain unchanged."
    print("move_to method test passed.")
    '''
    fs.client.rmr("/2")  # 确保目录不存在
    #fs.ensure_directory("/2")  # 确保目录存在
    fs.create_directory("/2")  # 创建目录
    #fs.remove("/2")
    fs.write_file("/2/1.txt", b"hello")   # ✔ 首次调用不会再抛 OSError

    #fs.remove("/2/1.txt")  # 尝试删除不存在的文件，应该不会抛出异常
    #fs.remove("/2/3.t")
    fs.remove("/2")  # 删除目录    
    #print(fs.get_node("/2").get_meta("type"))
    #assert fs.get_node("/2").get_meta("type") == "directory"
    #assert fs.get_node("/2/1.txt").read() == b"hello"


if __name__ == "__main__":
    main()
