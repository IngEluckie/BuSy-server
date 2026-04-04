from __future__ import annotations

import csv
from datetime import datetime
from time import sleep
from typing import Any, Dict, Iterable, Optional, Tuple

from utilities.projects.tasks.systemActivities.activityList import ActivityList
from utilities.projects.tasks.systemTask import SystemTask, now_mx
from utilities.projects.tasks.task import Status
from utilities.terminalTools import CsvManager, Logger


class Scheduler:
    LOG_HEADER: Tuple[str, ...] = (
        "record_id",
        "timestamp",
        "task_id",
        "task_name",
        "handler_name",
        "event",
        "status",
        "run_count",
        "retry_count",
        "max_retries",
        "next_run_at",
        "detail",
    )
    LEGACY_LOG_HEADER: Tuple[str, ...] = (
        "record_id",
        "timestamp",
        "activity_id",
        "activity_name",
        "event",
        "status",
        "detail",
    )

    def __init__(self) -> None:
        self.schedule_doc: CsvManager = CsvManager("Scheduler_activity_logs_document")
        self.runtime_doc: CsvManager = CsvManager("Scheduler_runtime_logs_document")
        self.logger: Logger = Logger(self.runtime_doc, debug_enabled=False)
        self.executeLoop: list[SystemTask] = []
        self._known_task_ids: set[str] = set()

        self._ensure_log_header()
        snapshots = self._retrieve_task_snapshots()

        for configured_name, task_builder in self._iter_initial_activities():
            try:
                task = self._coerce_task(task_builder, configured_name)
            except Exception as exc:
                self.logger.error(
                    f"No se pudo inicializar la actividad '{configured_name or task_builder}': {exc}"
                )
                continue

            if task.task_id in self._known_task_ids:
                self.logger.error(f"Task duplicada ignorada: {task.task_id}")
                continue

            snapshot = self._find_snapshot_for_task(task, snapshots)
            if snapshot is not None:
                task.restore_runtime(snapshot)

            if not self._should_enqueue_task(task):
                self.logger.info(
                    f"Actividad omitida al iniciar: {task.name} | estado={task.status.value}"
                )
                continue

            self.executeLoop.append(task)
            self._known_task_ids.add(task.task_id)
            self._log_task_event(
                task,
                event="restored" if snapshot else "registered",
                detail=(
                    "Task restored from scheduler log"
                    if snapshot
                    else "Task registered in scheduler execute loop"
                ),
            )

        self.logger.info(
            f"Scheduler inicializado con {len(self.executeLoop)} tarea(s) activa(s)"
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
            parsed_rows = list(reader)

        if not parsed_rows:
            return rows

        active_header = self._select_header(parsed_rows[0])
        start_index = 1 if tuple(self._trim_row(parsed_rows[0]))[0:1] == ("record_id",) else 0

        for raw_row in parsed_rows[start_index:]:
            trimmed = self._trim_row(raw_row)
            if not trimmed:
                continue
            if trimmed[0] == "record_id":
                continue

            padded = trimmed + [""] * (len(active_header) - len(trimmed))
            mapped = dict(zip(active_header, padded[: len(active_header)]))
            normalized = self._normalize_log_row(mapped)
            rows.append(normalized)

        return rows

    def _select_header(self, first_row: list[str]) -> Tuple[str, ...]:
        trimmed = tuple(self._trim_row(first_row))
        if trimmed == self.LOG_HEADER:
            return self.LOG_HEADER
        if trimmed == self.LEGACY_LOG_HEADER:
            return self.LEGACY_LOG_HEADER
        if trimmed and trimmed[0] == "record_id":
            return tuple(trimmed)
        return self.LEGACY_LOG_HEADER

    def _trim_row(self, row: list[str]) -> list[str]:
        trimmed = list(row)
        while trimmed and trimmed[-1] == "":
            trimmed.pop()
        return trimmed

    def _normalize_log_row(self, row: Dict[str, str]) -> Dict[str, str]:
        normalized = dict(row)
        if "activity_id" in normalized and "task_id" not in normalized:
            normalized["task_id"] = normalized.get("activity_id", "")
        if "activity_name" in normalized and "task_name" not in normalized:
            normalized["task_name"] = normalized.get("activity_name", "")

        normalized.setdefault("task_id", "")
        normalized.setdefault("task_name", "")
        normalized.setdefault("handler_name", "")
        normalized.setdefault("event", "")
        normalized.setdefault("status", "")
        normalized.setdefault("run_count", "")
        normalized.setdefault("retry_count", "")
        normalized.setdefault("max_retries", "")
        normalized.setdefault("next_run_at", "")
        normalized.setdefault("detail", "")
        return normalized

    def _retrieve_task_snapshots(self) -> Dict[str, Dict[str, str]]:
        snapshots: Dict[str, Dict[str, str]] = {}

        for row in self._read_log_rows():
            key = row.get("task_id") or row.get("task_name")
            if not key:
                continue
            snapshots[key] = row

        return snapshots

    def _find_snapshot_for_task(
        self, task: SystemTask, snapshots: Dict[str, Dict[str, str]]
    ) -> Dict[str, str] | None:
        return snapshots.get(task.task_id) or snapshots.get(task.name)

    def _coerce_task(self, task_builder: Any, configured_name: Optional[str]) -> SystemTask:
        candidate = task_builder() if callable(task_builder) else task_builder
        if not isinstance(candidate, SystemTask):
            raise TypeError("La actividad debe devolver una instancia de SystemTask.")

        if configured_name and not candidate.name:
            candidate.name = str(configured_name)

        return candidate

    def _should_enqueue_task(self, task: SystemTask) -> bool:
        if not task.enabled:
            return False
        if task.status in {Status.CANCELLED, Status.SKIPPED, Status.FAILED}:
            return False
        if task.status == Status.DONE and not task.is_recurrent():
            return False
        return True

    def _log_task_event(self, task: SystemTask, *, event: str, detail: str = "") -> None:
        self.schedule_doc.addEntry(task.to_log_row(event=event, detail=detail))

    def addActivity(
        self, task_or_factory: SystemTask | Any, task_name: Optional[str] = None
    ) -> SystemTask:
        task = self._coerce_task(task_or_factory, task_name)
        if task.task_id in self._known_task_ids:
            raise ValueError(f"Task ID duplicado: {task.task_id}")

        self.executeLoop.append(task)
        self._known_task_ids.add(task.task_id)
        self._log_task_event(task, event="registered", detail="Task added dynamically")
        return task

    def deleteActivity(self, identifier: str) -> bool:
        for index, task in enumerate(self.executeLoop):
            if task.task_id != identifier and task.name != identifier:
                continue

            removed = self.executeLoop.pop(index)
            removed.enabled = False
            removed.status = Status.SKIPPED
            self._known_task_ids.discard(removed.task_id)
            self._log_task_event(
                removed,
                event="deleted",
                detail="Task removed from scheduler execute loop",
            )
            return True

        return False

    def getExecuteLoop(self) -> Tuple[SystemTask, ...]:
        return tuple(self.executeLoop)

    def _run_task(self, task: SystemTask) -> None:
        task.mark_running(now_mx())
        self._log_task_event(task, event="started", detail=f"Run #{task.run_count}")

        try:
            result = task.run()
        except Exception as exc:
            task.mark_failure(now_mx(), exc)
            if task.status == Status.PENDING:
                self._log_task_event(
                    task,
                    event="retry_scheduled",
                    detail=f"{task.last_error} | retry {task.retry_count}/{task.max_retries}",
                )
            else:
                self._log_task_event(task, event="failed", detail=task.last_error or "")
                self.logger.error(f"{task.to_scheduler_log('failed')} | error={task.last_error}")
            return

        task.mark_success(now_mx(), result)
        detail = "Task completed successfully" if result is None else str(result)
        self._log_task_event(task, event="completed", detail=detail)

    def run(self, stop_event=None, poll_interval: float = 1.0) -> None:
        while True:
            if stop_event is not None and stop_event.is_set():
                self.logger.info("Scheduler detenido por stop_event")
                break

            current_time = now_mx()
            for task in self.executeLoop:
                if stop_event is not None and stop_event.is_set():
                    break
                if not task.can_run(current_time):
                    continue
                self._run_task(task)

            sleep(poll_interval)
