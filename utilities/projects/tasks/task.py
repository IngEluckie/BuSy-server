# task.py

from pydantic import BaseModel
from terminalTools import FechaHora
from tags.tag import Tag
from typing import Tuple
from enum import Enum

class Priority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MID = "MID"
    LOW = "LOW"

class Status(str, Enum):
    PENDING = "PENDING"
    DONE = "DONE"
    CANCELLED = "CANCELLED"
    POSTPOSED = "POSTPOSED"
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

#now: fechaHora = FechaHora().registro
class Task(BaseModel):
    """
    Minimum unit for Schedule management
    """
    name: str
    date: FechaHora
    tags: Tuple[Tag, ...]
    description: str
    priority: Priority
    status: Status
    type: TaskType
    #is_internal: bool # Is internal activity of the system?
    repeat: Repeat
