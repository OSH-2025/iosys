from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    timestamp: datetime
    level: LogLevel
    name: str
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "name": self.name,
            "message": self.message,
        }


all_logs: List[LogEntry] = []


class IOSYSLogger:
    def __init__(self, name: str, all_logs=all_logs):
        self.name = name
        self.logs: List[LogEntry] = all_logs

    def _log(self, level: LogLevel, message: str):
        entry = LogEntry(
            timestamp=datetime.now(), level=level, name=self.name, message=message
        )
        self.logs.append(entry)
        print(f"[{level.value}] [{self.name}] {message}")

    def debug(self, message: str):
        self._log(LogLevel.DEBUG, message)

    def info(self, message: str):
        self._log(LogLevel.INFO, message)

    def warning(self, message: str):
        self._log(LogLevel.WARNING, message)

    def error(self, message: str):
        self._log(LogLevel.ERROR, message)

    def critical(self, message: str):
        self._log(LogLevel.CRITICAL, message)

    def get_logs(self, level: Optional[LogLevel] = None) -> List[LogEntry]:
        if level is None:
            return self.logs.copy()
        return [log for log in self.logs if log.level == level]

    def clear_logs(self):
        self.logs.clear()
