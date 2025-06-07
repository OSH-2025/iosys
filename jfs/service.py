import os
import subprocess
import atexit
import psutil


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
        self.pid_file = os.environ.get('JFS_PID_FILE')
        atexit.register(self.stop)
        self._recover_process()

    def _read_pid(self):
        """Read PID from PID file"""
        if not self.pid_file or not os.path.exists(self.pid_file):
            return None
        try:
            with open(self.pid_file, 'r') as f:
                return int(f.read().strip())
        except (ValueError, IOError):
            return None

    def _write_pid(self, pid):
        """Write PID to PID file"""
        if self.pid_file:
            try:
                os.makedirs(os.path.dirname(self.pid_file), exist_ok=True)
                with open(self.pid_file, 'w') as f:
                    f.write(str(pid))
            except IOError:
                pass

    def _delete_pid(self):
        """Delete PID file"""
        if self.pid_file and os.path.exists(self.pid_file):
            try:
                os.remove(self.pid_file)
            except IOError:
                pass

    def _recover_process(self):
        """Recover process from PID file if it exists"""
        pid = self._read_pid()
        if pid:
            try:
                process = psutil.Process(pid)
                if process.is_running() and 'juicefs' in process.name().lower():
                    # Don't set self.process as we didn't start it directly
                    pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self._delete_pid()

    def is_running(self):
        """Check if JuiceFS service is currently running"""
        # Check our own process first
        if self.process is not None and self.process.poll() is None:
            return True
        
        # Check PID file for external process
        pid = self._read_pid()
        if pid:
            try:
                process = psutil.Process(pid)
                return process.is_running() and 'juicefs' in process.name().lower()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self._delete_pid()
                return False
        
        return False

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

        # Write PID to file for persistence
        self._write_pid(self.process.pid)
        
        return self.process

    def stop(self):
        """Stop JuiceFS service"""
        stopped = False
        
        # Stop our own process first
        if self.is_running() and self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
                stopped = True
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
                stopped = True
            self.process = None
        
        # Handle external process from PID file
        pid = self._read_pid()
        if pid:
            try:
                process = psutil.Process(pid)
                if process.is_running() and 'juicefs' in process.name().lower():
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                        stopped = True
                    except psutil.TimeoutExpired:
                        process.kill()
                        stopped = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Clean up PID file
        self._delete_pid()
        
        return stopped

    def restart(self):
        """Restart JuiceFS service"""
        self.stop()
        return self.start()
