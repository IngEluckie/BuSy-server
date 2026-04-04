from __future__ import annotations

from typing import Callable

from utilities.projects.tasks.systemActivities.node_synching.node_sync import (
    build_node_sync_task,
)
from utilities.projects.tasks.systemTask import SystemTask


ActivityFactory = Callable[[], SystemTask]

ActivityList: dict[str, list[ActivityFactory]] = {
    "systemActivities": [build_node_sync_task],
}
