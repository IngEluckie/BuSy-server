# scheduler.py

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime
from time import sleep
from typing import Any, Dict, Iterable, Optional, Tuple

try:
    from zoneinfo import ZoneInfo

    MX_TZ = ZoneInfo("America/Mexico_City")
except Exception:
    MX_TZ = None

from utilities.projects.tasks.systemActivities.activityList import ActivityList
from utilities.terminalTools import CsvManager, Logger


def now_mx() -> datetime:
    if MX_TZ:
        return datetime.now(MX_TZ)
    return datetime.now()


def gen_id(prefix: str = "act") -> str:
    timestamp = now_mx().strftime("%Y%m%d%H%M%S%f")
    return f"{prefix}_{timestamp}"


@dataclass
class ScheduledActivity:
    activity_id: str
    name: str
    runner: Any
    original: Any
    status: str = "PENDING"
    metadata: Dict[str, Any] = field(default_factory=dict)
    run_count: int = 0
    retry_count: int = 0
    max_retries: int = 0
    last_run_at: Optional[datetime] = None
    last_error: Optional[str] = None


class Scheduler:
    LOG_HEADER: Tuple[str, ...] = (
        "record_id",
        "timestamp",
        "activity_id",
        "activity_name",
        "event",
        "status",
        "detail",
    )
    TERMINAL_STATUSES = {"DONE", "FAILED", "SKIPPED"}

    def __init__(self) -> None:
        self.schedule_doc: CsvManager = CsvManager("Scheduler_activity_logs_document")
        self.runtime_doc: CsvManager = CsvManager("Scheduler_runtime_logs_document")
        self.logger: Logger = Logger(self.runtime_doc, debug_enabled=False)
        self.executeLoop: list[ScheduledActivity] = []

        self._ensure_log_header()
        already_done = set(self._retrieveActivities())

        for configured_name, activity_builder in self._iter_initial_activities():
            try:
                activity = self._build_activity(activity_builder, configured_name)
            except Exception as exc:
                self.logger.error(
                    f"No se pudo inicializar la actividad '{configured_name or activity_builder}': {exc}"
                )
                continue

            if activity.name in already_done:
                self.logger.info(
                    f"Actividad omitida al iniciar porque ya estaba completada: {activity.name}"
                )
                continue

            self.executeLoop.append(activity)
            self._log_activity_event(
                activity,
                event="registered",
                status=activity.status,
                detail="Activity registered in scheduler execute loop",
            )

        self.logger.info(
            f"Scheduler inicializado con {len(self.executeLoop)} actividad(es) pendiente(s)"
        )

    def _initialActivities(self) -> list:
        return ActivityList["systemActivities"]

    def _iter_initial_activities(self) -> Iterable[Tuple[Optional[str], Any]]:
        initial_activity_list = self._initialActivities()

        if isinstance(initial_activity_list, dict):
            return initial_activity_list.items()
        return ((None, activity) for activity in initial_activity_list)

    def _ensure_log_header(self) -> None:
        path = self.schedule_doc.filepath

        if not path.exists() or path.stat().st_size == 0:
            self.schedule_doc.addEntry(self.LOG_HEADER)
            return

        with path.open("r", encoding="utf-8", newline="") as current_file:
            reader = csv.reader(current_file)
            first_row = next(reader, [])

        while first_row and first_row[-1] == "":
            first_row.pop()

        if tuple(first_row) != self.LOG_HEADER:
            self.schedule_doc.addTopRow(self.LOG_HEADER)

    def _read_log_rows(self) -> list[Dict[str, str]]:
        rows: list[Dict[str, str]] = []

        if not self.schedule_doc.filepath.exists():
            return rows

        with self.schedule_doc.filepath.open("r", encoding="utf-8", newline="") as log_file:
            reader = csv.reader(log_file)
            for raw_row in reader:
                if not raw_row:
                    continue

                while raw_row and raw_row[-1] == "":
                    raw_row.pop()

                if not raw_row or tuple(raw_row) == self.LOG_HEADER:
                    continue

                padded_row = raw_row + [""] * (len(self.LOG_HEADER) - len(raw_row))
                row_map = dict(zip(self.LOG_HEADER, padded_row[: len(self.LOG_HEADER)]))
                rows.append(row_map)

        return rows

    def _retrieveActivities(self) -> list[str]:
        latest_status_by_activity: Dict[str, str] = {}

        for row in self._read_log_rows():
            activity_name = row.get("activity_name", "").strip()
            status = row.get("status", "").strip()
            if not activity_name:
                continue
            latest_status_by_activity[activity_name] = status

        return [
            activity_name
            for activity_name, status in latest_status_by_activity.items()
            if status == "DONE"
        ]

    def _build_activity(self, activity_builder: Any, configured_name: Optional[str]) -> ScheduledActivity:
        instance = activity_builder() if callable(activity_builder) else activity_builder
        metadata = self._extract_metadata(instance)
        activity_name = configured_name or metadata.get("name") or getattr(instance, "name", None)
        activity_name = activity_name or instance.__class__.__name__
        runner = self._resolve_runner(instance)
        max_retries = self._safe_int(metadata.get("max_retries", 0))

        return ScheduledActivity(
            activity_id=gen_id(),
            name=str(activity_name),
            runner=runner,
            original=instance,
            metadata=metadata,
            max_retries=max_retries,
        )

    def _extract_metadata(self, instance: Any) -> Dict[str, Any]:
        raw_metadata = getattr(instance, "metadata", {})
        if isinstance(raw_metadata, dict):
            return dict(raw_metadata)
        return {}

    def _resolve_runner(self, instance: Any) -> Any:
        public_runner = getattr(instance, "run", None)
        if callable(public_runner):
            return public_runner

        private_runner = getattr(instance, "_run", None)
        if callable(private_runner):
            return private_runner

        raise TypeError("La actividad no expone un método 'run()' o '_run()'")

    def _safe_int(self, value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _log_activity_event(
        self,
        activity: ScheduledActivity,
        *,
        event: str,
        status: str,
        detail: str = "",
    ) -> None:
        timestamp = now_mx().isoformat()
        self.schedule_doc.addEntry(
            (
                gen_id("log"),
                timestamp,
                activity.activity_id,
                activity.name,
                event,
                status,
                detail,
            )
        )

    def addActivity(self, activity_builder: Any, activity_name: Optional[str] = None) -> ScheduledActivity:
        activity = self._build_activity(activity_builder, activity_name)
        self.executeLoop.append(activity)
        self._log_activity_event(
            activity,
            event="registered",
            status=activity.status,
            detail="Activity added dynamically",
        )
        return activity

    def deleteActivity(self, activity_name: str) -> bool:
        for index, activity in enumerate(self.executeLoop):
            if activity.name != activity_name:
                continue

            removed = self.executeLoop.pop(index)
            removed.status = "SKIPPED"
            self._log_activity_event(
                removed,
                event="deleted",
                status=removed.status,
                detail="Activity removed from scheduler execute loop",
            )
            return True

        return False

    def getExecuteLoop(self) -> Tuple[ScheduledActivity, ...]:
        return tuple(self.executeLoop)

    def _can_run(self, activity: ScheduledActivity) -> bool:
        return activity.status == "PENDING"

    def _run_activity(self, activity: ScheduledActivity) -> None:
        activity.status = "RUNNING"
        activity.run_count += 1
        activity.last_run_at = now_mx()
        self._log_activity_event(
            activity,
            event="started",
            status=activity.status,
            detail=f"Run #{activity.run_count}",
        )

        try:
            result = activity.runner()
        except Exception as exc:
            activity.last_error = str(exc)
            if activity.retry_count < activity.max_retries:
                activity.retry_count += 1
                activity.status = "PENDING"
                self._log_activity_event(
                    activity,
                    event="retry_scheduled",
                    status=activity.status,
                    detail=(
                        f"{activity.last_error} | retry "
                        f"{activity.retry_count}/{activity.max_retries}"
                    ),
                )
            else:
                activity.status = "FAILED"
                self._log_activity_event(
                    activity,
                    event="failed",
                    status=activity.status,
                    detail=activity.last_error,
                )
                self.logger.error(f"Actividad fallida: {activity.name} | {activity.last_error}")
            return

        detail = "Activity completed successfully"
        if result is not None:
            detail = str(result)

        activity.last_error = None
        activity.status = "DONE"
        self._log_activity_event(
            activity,
            event="completed",
            status=activity.status,
            detail=detail,
        )

    def run(self, stop_event=None, poll_interval: float = 1.0) -> None:
        while True:
            if stop_event is not None and stop_event.is_set():
                self.logger.info("Scheduler detenido por stop_event")
                break

            for activity in self.executeLoop:
                if stop_event is not None and stop_event.is_set():
                    break
                if not self._can_run(activity):
                    continue
                self._run_activity(activity)

            sleep(poll_interval)
