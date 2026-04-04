import unittest
from datetime import timedelta

from utilities.projects.tasks.systemTask import SystemTask, now_mx
from utilities.projects.tasks.task import Repeat, Status, TaskType
from utilities.scheduler.Scheduler import Scheduler


class IsolatedScheduler(Scheduler):
    def _initialActivities(self) -> list:
        return []


def build_dummy_task(task_id: str = "test.dummy") -> SystemTask:
    task = SystemTask(
        task_id=task_id,
        name=f"Dummy-{task_id}",
        description="Dummy task for scheduler tests.",
    )
    task.bind_runner(lambda: "ok")
    return task


class SchedulerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scheduler = IsolatedScheduler()
        self.scheduler.executeLoop.clear()

    def test_system_task_marks_unique_task_as_done(self) -> None:
        task = build_dummy_task("test.unique")
        task.mark_running(now_mx())
        task.mark_success(now_mx(), "ok")

        self.assertEqual(task.status, Status.DONE)
        self.assertIsNone(task.next_run_at)

    def test_system_task_recurrent_task_reschedules_itself(self) -> None:
        task = SystemTask(
            task_id="test.recurrent",
            name="Dummy-recurrent",
            description="Recurring test task.",
            type=TaskType.CRON,
            repeat=Repeat.DAILY,
        )
        task.bind_runner(lambda: "ok")

        started_at = now_mx()
        task.mark_running(started_at)
        task.mark_success(started_at, "ok")

        self.assertEqual(task.status, Status.PENDING)
        self.assertIsNotNone(task.next_run_at)
        self.assertGreaterEqual(task.next_run_at, started_at + timedelta(days=1))

    def test_add_activity_registers_system_task(self) -> None:
        task = self.scheduler.addActivity(build_dummy_task("test.added"))

        self.assertEqual(task.task_id, "test.added")
        self.assertEqual(len(self.scheduler.getExecuteLoop()), 1)

    def test_run_task_marks_it_done(self) -> None:
        task = self.scheduler.addActivity(build_dummy_task("test.run"))
        self.scheduler._run_task(task)

        self.assertEqual(task.status, Status.DONE)


if __name__ == "__main__":
    unittest.main()
