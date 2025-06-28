# test_cache.py
from fs import new_fs
import asyncio


async def run_tests():
    fs = new_fs()

    # Test creating a directory
    print("Testing directory creation...")
    dir_path = "/test_dir"
    dir_node = fs.create_directory(dir_path)
    assert dir_node.path == dir_path, "Directory creation failed."
    print("Directory creation test passed.")

    # Test writing a file
    print("Testing file writing...")
    file_path = "/test_dir/test_file.txt"
    content = b"Hello, Cache!"
    file_node = fs.write_file(file_path, content)
    assert file_node.path == file_path, "File writing failed."
    assert fs.read(file_path) == content, "File content mismatch."
    print("File writing test passed.")

    # Test moving a file
    print("Testing file moving...")
    new_file_path = "/test_dir/moved_file.txt"
    fs.move(file_path, new_file_path)
    assert fs.get_node(file_path) is None, "Old file path should not exist."
    assert fs.read(new_file_path) == content, "Moved file content mismatch."
    print("File moving test passed.")

    # Test removing a file
    print("Testing file removal...")
    fs.remove(new_file_path)
    assert fs.get_node(new_file_path) is None, "File removal failed."
    print("File removal test passed.")

    # Test removing a directory
    print("Testing directory removal...")
    fs.remove(dir_path)
    assert fs.get_node(dir_path) is None, "Directory removal failed."
    print("Directory removal test passed.")

    print("All tests passed.")


if __name__ == "__main__":
    asyncio.run(run_tests())
