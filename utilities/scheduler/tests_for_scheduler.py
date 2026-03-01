import unittest

from utilities.scheduler.scheduler import Scheduler


class DummyActivity:
    def __init__(self) -> None:
        self.metadata = {"name": "dummy-activity"}

    def _run(self) -> str:
        return "ok"


class SchedulerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scheduler = Scheduler()
        self.scheduler.executeLoop.clear()

    def test_add_activity_registers_it(self) -> None:
        activity = self.scheduler.addActivity(DummyActivity)
        self.assertEqual(activity.name, "dummy-activity")
        self.assertEqual(len(self.scheduler.getExecuteLoop()), 1)

    def test_run_activity_marks_it_done(self) -> None:
        activity = self.scheduler.addActivity(DummyActivity)
        self.scheduler._run_activity(activity)
        self.assertEqual(activity.status, "DONE")


if __name__ == "__main__":
    unittest.main()
