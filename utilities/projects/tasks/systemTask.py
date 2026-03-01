# systemTask.py

from enum import Enum
from typing import Optional
from pydantic import Field

from task import Task


class SystemSource(str, Enum):
    SCHEDULER = "SCHEDULER"
    FILE_MANAGER = "FILE_MANAGER"
    SYNC = "SYNC"
    MAINTENANCE = "MAINTENANCE"
    OTHER = "OTHER"


class SystemVisibility(str, Enum):
    HIDDEN = "HIDDEN"
    READ_ONLY = "READ_ONLY"
    VISIBLE = "VISIBLE"


class RunMode(str, Enum):
    BACKGROUND = "BACKGROUND"
    FOREGROUND = "FOREGROUND"


class SystemTask(Task):
    # Internal identity and ownership
    is_internal: bool = True
    source: SystemSource = SystemSource.SCHEDULER
    owner_component: str = "scheduler"

    # UX and control
    editable_by_user: bool = False
    visibility: SystemVisibility = SystemVisibility.READ_ONLY
    run_mode: RunMode = RunMode.BACKGROUND

    # Runtime execution tracking
    run_count: int = Field(default=0, ge=0)
    retry_count: int = Field(default=0, ge=0)
    max_retries: int = Field(default=1, ge=0)
    last_error: Optional[str] = None
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None

    def to_scheduler_log(self, event: str) -> str:
        """
        Compact text for Logger.newLog/info/warning/error.
        The logger already persists timestamp via terminalTools.FechaHora.
        """
        return (
            f"{event} | task={self.name} | source={self.source.value} "
            f"| status={self.status.value} | run={self.run_count} "
            f"| retry={self.retry_count}/{self.max_retries}"
        )
