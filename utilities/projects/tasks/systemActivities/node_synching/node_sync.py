from __future__ import annotations

from utilities.projects.tasks.systemTask import SystemSource, SystemTask
from utilities.projects.tasks.task import Repeat, TaskType


class NSync:
    def run(self) -> str:
        print("Iniciando actividad de sincronizacion")
        return "Node sync placeholder finished"


def build_node_sync_task() -> SystemTask:
    worker = NSync()
    task = SystemTask(
        task_id="system.node_sync",
        name="NSync",
        description="Synchronize business nodes and shared state.",
        handler_name="node_sync",
        source=SystemSource.SYNC,
        owner_component="node_sync",
        type=TaskType.UNIQUE,
        repeat=Repeat.NEVER,
        max_retries=1,
    )
    task.bind_runner(worker.run)
    return task
