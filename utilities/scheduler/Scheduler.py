# scheduler.py

from typing import Tuple

class Scheduler:

    """
    PROCESS LOOP:
    - Check
    - Manage: Add, Delete, Configure
    - Coordinate
    - Report


    - De las actividades pendientes, cuales son para hoy agendadas?
    """

    def _retrieveActivities(self,) -> Tuple:
        return []

    def __init__(self) -> None:
        # First gotta retrieve its activity list
        # Where? Activity log?
        self.executeLoop: Tuple = []
        pass

    def addActivity(self,):
        pass

    def deleteActivity(self,):
        pass

    def getExecuteLoop(self,) -> Tuple:
        return self.executeLoop

    def run(self,): 
        pass