import os
import subprocess
import atexit


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


class JuiceFSService:
    def __init__(self):
        self.process = None
        atexit.register(self.stop)

    def is_running(self):
        """Check if JuiceFS service is currently running"""
        return self.process is not None and self.process.poll() is None

    def start(self):
        """Start JuiceFS service"""
        if self.is_running():
            raise RuntimeError("JuiceFS service is already running")

        command = [
            "juicefs",
            "mount",
            f"--cache-dir={os.environ.get('JFS_CACHE_DIR')}",
            os.environ.get("JFS_META_URL"),
            os.environ.get("JFS_MOUNTPOINT"),
        ]

        log_file = os.environ.get("JFS_LOG_FILE")
        with open(log_file, "w") as f:
            self.process = subprocess.Popen(
                command,
                stdout=f,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW
                if hasattr(subprocess, "CREATE_NO_WINDOW")
                else 0,
            )

        return self.process

    def stop(self):
        """Stop JuiceFS service"""
        if self.is_running():
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.process = None

    def restart(self):
        """Restart JuiceFS service"""
        self.stop()
        return self.start()
