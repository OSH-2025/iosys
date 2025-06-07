import os
import subprocess


def init_jfs_environment():
    """Initialize JuiceFS environment by formatting the filesystem"""
    command = [
        "juicefs",
        "format",
        "--storage=file",
        f"--bucket={os.environ.get('JFS_BUCKET')}",
        f"{os.environ.get('JFS_META_URL')}?mode=rwc",
        os.environ.get("JFS_NAME"),
    ]

    subprocess.run(command, check=True)


def start_jfs_service():
    """Start JuiceFS service in the background"""
    command = [
        "juicefs",
        "mount",
        f"--cache-dir={os.environ.get('JFS_CACHE_DIR')}",
        os.environ.get("JFS_META_URL"),
        os.environ.get("JFS_MOUNTPOINT"),
    ]

    log_file = os.environ.get("JFS_LOG_FILE")
    with open(log_file, "a") as f:
        process = subprocess.Popen(
            command,
            stdout=f,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW
            if hasattr(subprocess, "CREATE_NO_WINDOW")
            else 0,
        )

    return process
