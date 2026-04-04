from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Tuple

from pydantic import BaseModel, ConfigDict

from utilities.projects.tasks.tags.tag import Tag


class Priority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MID = "MID"
    LOW = "LOW"


class Status(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    POSTPOSED = "POSTPOSED"
    SKIPPED = "SKIPPED"
    LOST = "LOST"


class TaskType(str, Enum):
    UNIQUE = "UNIQUE"
    CRON = "CRON"


class Repeat(str, Enum):
    NEVER = "NEVER"
    DAILY = "DAILY"
    WEEKDAYS = "WEEKDAYS"
    WEEKEND = "WEEKEND"
    TWOWEEKS = "TWOWEEKS"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class Task(BaseModel):
    """
    Minimum unit for schedule management.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)

    name: str
    description: str = ""
    date: datetime | None = None
    tags: Tuple[Tag, ...] = ()
    priority: Priority = Priority.MID
    status: Status = Status.PENDING
    type: TaskType = TaskType.UNIQUE
    repeat: Repeat = Repeat.NEVER
