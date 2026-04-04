from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional
from uuid import uuid4

from pydantic import ConfigDict, Field, PrivateAttr

from utilities.projects.tasks.task import Repeat, Status, Task, TaskType

try:
    from zoneinfo import ZoneInfo

    MX_TZ = ZoneInfo("America/Mexico_City")
except Exception:
    MX_TZ = None


def now_mx() -> datetime:
    if MX_TZ:
        return datetime.now(MX_TZ)
    return datetime.now()


def ensure_tz(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if MX_TZ and value.tzinfo is None:
        return value.replace(tzinfo=MX_TZ)
    return value


def gen_task_id(prefix: str = "sys") -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


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
    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)

    # Stable identity
    task_id: str = Field(default_factory=gen_task_id)
    handler_name: str = "system_task"
    enabled: bool = True

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
    max_retries: int = Field(default=0, ge=0)
    last_error: Optional[str] = None
    last_run_at: datetime | None = None
    last_finished_at: datetime | None = None
    next_run_at: datetime | None = None

    _runner: Optional[Callable[[], Any]] = PrivateAttr(default=None)

    def bind_runner(self, runner: Callable[[], Any]) -> None:
        if not callable(runner):
            raise TypeError("SystemTask runner must be callable.")
        self._runner = runner

    def has_runner(self) -> bool:
        return self._runner is not None

    def run(self) -> Any:
        if self._runner is None:
            raise RuntimeError(f"SystemTask '{self.name}' has no runner bound.")
        return self._runner()

    def is_recurrent(self) -> bool:
        return self.type == TaskType.CRON or self.repeat != Repeat.NEVER

    def scheduled_for(self) -> datetime | None:
        return ensure_tz(self.next_run_at or self.date)

    def can_run(self, now: datetime | None = None) -> bool:
        current = ensure_tz(now or now_mx())
        scheduled_for = self.scheduled_for()

        if not self.enabled:
            return False
        if self._runner is None:
            return False
        if self.status != Status.PENDING:
            return False
        if scheduled_for is None:
            return True
        return scheduled_for <= current

    def mark_running(self, now: datetime | None = None) -> None:
        current = ensure_tz(now or now_mx())
        self.status = Status.RUNNING
        self.run_count += 1
        self.last_run_at = current

    def mark_success(self, now: datetime | None = None, result: Any = None) -> Any:
        current = ensure_tz(now or now_mx())
        self.last_error = None
        self.retry_count = 0
        self.last_finished_at = current

        if self.is_recurrent():
            self.schedule_next_run(current)
            self.status = Status.PENDING if self.next_run_at is not None else Status.DONE
        else:
            self.status = Status.DONE
            self.next_run_at = None

        return result

    def mark_failure(self, now: datetime | None = None, error: Exception | str = "") -> None:
        current = ensure_tz(now or now_mx())
        self.last_error = str(error)
        self.last_finished_at = current

        if self.retry_count < self.max_retries:
            self.retry_count += 1
            self.status = Status.PENDING
            self.next_run_at = current
            return

        self.status = Status.FAILED

    def schedule_next_run(self, now: datetime | None = None) -> datetime | None:
        current = ensure_tz(now or now_mx())

        if not self.is_recurrent():
            self.next_run_at = None
            return None

        if self.repeat == Repeat.NEVER:
            self.next_run_at = None
            return None

        if self.repeat == Repeat.DAILY:
            self.next_run_at = current + timedelta(days=1)
            return self.next_run_at

        if self.repeat == Repeat.WEEKDAYS:
            next_run = current + timedelta(days=1)
            while next_run.weekday() >= 5:
                next_run += timedelta(days=1)
            self.next_run_at = next_run
            return self.next_run_at

        if self.repeat == Repeat.WEEKEND:
            next_run = current + timedelta(days=1)
            while next_run.weekday() < 5:
                next_run += timedelta(days=1)
            self.next_run_at = next_run
            return self.next_run_at

        if self.repeat == Repeat.TWOWEEKS:
            self.next_run_at = current + timedelta(days=14)
            return self.next_run_at

        if self.repeat == Repeat.MONTHLY:
            year = current.year + (1 if current.month == 12 else 0)
            month = 1 if current.month == 12 else current.month + 1
            day = min(current.day, monthrange(year, month)[1])
            self.next_run_at = current.replace(year=year, month=month, day=day)
            return self.next_run_at

        if self.repeat == Repeat.YEARLY:
            year = current.year + 1
            day = current.day
            if current.month == 2 and current.day == 29 and monthrange(year, 2)[1] == 28:
                day = 28
            self.next_run_at = current.replace(year=year, day=day)
            return self.next_run_at

        self.next_run_at = None
        return None

    def restore_runtime(self, snapshot: dict[str, str]) -> None:
        status_value = snapshot.get("status")
        if status_value in Status._value2member_map_:
            self.status = Status(status_value)
        if self.status == Status.RUNNING:
            self.status = Status.PENDING

        self.run_count = self._parse_int(snapshot.get("run_count"), self.run_count)
        self.retry_count = self._parse_int(snapshot.get("retry_count"), self.retry_count)
        self.max_retries = self._parse_int(snapshot.get("max_retries"), self.max_retries)
        self.next_run_at = self._parse_datetime(snapshot.get("next_run_at")) or self.next_run_at

        detail = snapshot.get("detail", "")
        event = snapshot.get("event", "")
        if event in {"failed", "retry_scheduled"} and detail:
            self.last_error = detail

        if self.is_recurrent() and self.status == Status.DONE:
            self.status = Status.PENDING

    def to_log_row(self, event: str, detail: str = "") -> tuple[str, ...]:
        next_run_at = self.next_run_at.isoformat() if self.next_run_at else ""
        return (
            f"log_{uuid4().hex[:12]}",
            now_mx().isoformat(),
            self.task_id,
            self.name,
            self.handler_name,
            event,
            self.status.value,
            str(self.run_count),
            str(self.retry_count),
            str(self.max_retries),
            next_run_at,
            detail,
        )

    def to_scheduler_log(self, event: str) -> str:
        return (
            f"{event} | task={self.name} | handler={self.handler_name} "
            f"| source={self.source.value} | status={self.status.value} "
            f"| run={self.run_count} | retry={self.retry_count}/{self.max_retries}"
        )

    @staticmethod
    def _parse_int(value: str | None, default: int) -> int:
        try:
            return int(value) if value not in (None, "") else default
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return ensure_tz(datetime.fromisoformat(value))
        except ValueError:
            return None
