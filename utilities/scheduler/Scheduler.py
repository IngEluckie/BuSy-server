# scheduler.py

# Import libraríes
import os
from time import sleep
import sys
from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import Tuple, Any, Optional, Dict
try:
    # Requiere Python 3.9+
    from zoneinfo import ZoneInfo
    MX_TZ = ZoneInfo("America/Mexico_City")
except Exception:
    MX_TZ = None
from utilities.terminalTools import CsvManager, Logger

# --------- Helpers ---------
def now_mx() -> datetime:
    """Fecha/hora actual con zona de America/Mexico_City (o naive si no disponible)."""
    if MX_TZ:
        return datetime.now(MX_TZ)
    return datetime.now()

def ensure_tz(dt: Optional[datetime]) -> Optional[datetime]:
    """Asegura que la fecha tenga zona horaria de MX si existe y viene naive."""
    if dt is None:
        return None
    if MX_TZ and dt.tzinfo is None:
        return dt.replace(tzinfo=MX_TZ)
    return dt

def gen_id(prefix: str = "tsk") -> str:
    """ID corto estable por timestamp (suficiente para logs y correlación)."""
    ts = now_mx().strftime("%Y%m%d%H%M%S%f")
    return f"{prefix}_{ts}"
# -------------------------------

# --------- FechaHora (helper para logs legibles) ---------
@dataclass
class FechaHora:
    """
    Helper para imprimir marcas de tiempo legibles en logs.
    Ejemplo: [11/Aug/2025 20:41:36]
    """
    registro: str = field(init=False)
    timestamp: datetime = field(default_factory=now_mx)

    def __post_init__(self):
        self.registro = self.timestamp.strftime("[%d/%b/%Y]")

# ---------- Fortmatos de datos ----------
@dataclass
class Registro:
    """
    Fila estructurada para ActivityLog (CSV).
    NOTA: 'id' puede ser asignado por CsvManager (autoincrement); por eso es opcional.
    """
    #Kind: Kind
    event: str
    when: datetime = field(default_factory=now_mx)
    task_id: int = None
    pass

class Scheduler:

    """
    PROCESS LOOP:
    - Check
    - Manage: Add, Delete, Configure
    - Coordinate
    - Report


    - De las actividades pendientes, cuales son para hoy agendadas?


    RULES
    1.- Start by checking what to do
    2.- What have been done
    3.- Whats left to do
    4.- Start activity and finish it
    5.- Refresh execute loop
    6.- After finishes one activiy, and before the other; accepst mmodification in the execute loop
    6.- Continue with next activity
    """

    def _retrieveActivities(self,) -> Tuple:
        return []

    def __init__(self) -> None:
        # First gotta retrieve its activity list
        # Where? Activity log?

        self.executeLoop: Tuple = []
        print("Scheduler init")
        

    def addActivity(self,):
        pass

    def deleteActivity(self,):
        pass

    def getExecuteLoop(self,) -> Tuple:
        return self.executeLoop

    def run(self, stop_event=None, poll_interval: float = 1.0):
        while True:
            if stop_event is not None and stop_event.is_set():
                break
            # TODO: ejecutar aqui el ciclo de tareas del scheduler
            sleep(poll_interval)
