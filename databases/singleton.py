# singleton.py

import sqlite3
from pathlib import Path
from sqlite3 import Error
from typing import Any, List, Optional, Tuple

from databases.bootstrap import initialize_database, needs_database_initialization
from utilities.handleDocument.document import BusyPaths


db_name: str = "main.sqlite3"


class Database:
    _instances: dict[str, "Database"] = {}

    def __new__(
        cls,
        db_path: str | Path | None = None,
        root_dir: str | Path | None = None,
    ) -> "Database":
        paths = BusyPaths(root_dir=root_dir)
        resolved_path = cls._resolve_db_path(paths, db_path)
        instance_key = str(resolved_path)

        if instance_key in cls._instances:
            return cls._instances[instance_key]

        try:
            instance = super(Database, cls).__new__(cls)
            instance._db_path = resolved_path
            instance.connection = sqlite3.connect(resolved_path, check_same_thread=False)
            instance.connection.row_factory = sqlite3.Row
            if needs_database_initialization(instance.connection):
                initialize_database(instance.connection, resolved_path)
            instance.cursor = instance.connection.cursor()
            cls._instances[instance_key] = instance
            print(f"Conexión a la base de datos establecida en: {resolved_path}")
            return instance
        except Error as e:
            print(f"Error al conectar con la base de datos {resolved_path.name}, error:\n {e}")
            raise

    @staticmethod
    def _resolve_db_path(paths: BusyPaths, db_path: str | Path | None) -> Path:
        if db_path is not None:
            custom_path = Path(db_path).expanduser()
            if not custom_path.is_absolute():
                custom_path = paths.project_root / custom_path
            custom_path.parent.mkdir(parents=True, exist_ok=True)
            return custom_path.resolve()

        return paths.ensure_runtime_database(filename=db_name).resolve()

    def execute_query(self, query: str, params: Tuple = ()) -> None:
        try:
            self.cursor.execute(query, params)
            self.connection.commit()
            print("Consulta ejecutada exitosamente.")
        except Error as e:
            print(f"Error al ejecutar la consulta: {e}")
            self.connection.rollback()

    def fetch_query(self, query: str, params: Tuple = ()) -> Optional[List[Any]]:
        try:
            self.cursor.execute(query, params)
            resultados = self.cursor.fetchall()
            result_list = [dict(row) for row in resultados]
            print("Consulta de selección ejecutada exitosamente.")
            return result_list
        except Error as e:
            print(f"Error al ejecutar la consulta de selección: {e}")
            return None

    def executemany(self, query: str, seq_params: List[Tuple]) -> None:
        try:
            self.cursor.executemany(query, seq_params)
            self.connection.commit()
            print("Consulta executemany ejecutada exitosamente.")
        except Error as e:
            print(f"Error en executemany: {e}")
            self.connection.rollback()

    def close_connection(self) -> None:
        connection = getattr(self, "connection", None)
        instance_key = str(getattr(self, "_db_path", ""))

        if connection is None:
            if instance_key:
                Database._instances.pop(instance_key, None)
            return

        try:
            cursor = getattr(self, "cursor", None)
            if cursor is not None:
                cursor.close()
            connection.close()
            print("Conexión a la base de datos cerrada")
        finally:
            if instance_key:
                Database._instances.pop(instance_key, None)
            self.connection = None
            self.cursor = None
