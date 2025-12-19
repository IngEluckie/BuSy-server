# singleton.py

# Importar librerías
import sqlite3
from sqlite3 import Error
from typing import Any, List, Tuple, Optional
import os

class Database:

    _instance = None
    # Obtenemos la ruta del directorio don de se encuentra este script
    _file_name: str = "systemDB.db"
    _base_dir: str = os.path.dirname(__file__)
    # Construir la ruta absoluta al arvhido de base de datos
    _db_path: str = os.path.join(_base_dir, _file_name)

    def __new__(cls):
        if cls._instance is None:
            try:
                cls._instance = super(Database, cls).__new__(cls)
                cls._instance.connection = sqlite3.connect(cls._db_path, check_same_thread=False)
                # Configuramos el row_factory para que las filas
                # se puedan convertir en directorios.
                cls._instance.connection.row_factory = sqlite3.Row
                cls._instance.cursor = cls._instance.connection.cursor()
                print(f"Conexión a la base de datos establecida en: {cls._db_path}")
            except Error as e:
                print(f"Error al conectar con la base de datos {cls._file_name}, error: \n {e}")
                cls._instance = None
        return cls._instance
    
    def execute_query(self, query: str, params: Tuple = ()) -> None:
        # Ejecuta una consulta SQL que no retorna resultados:
        # INSERT, UPDATE, DELETE, etc...
        try: 
            self.cursor.execute(query, params)
            self.connection.commit()
            print(f"Consulta ejecutada exitosamente.")
        except Error as e:
            print(f"Error al ejecutar la consulta: {e}")
            self.connection.rollback()

    def fetch_query(self, query: str, params: Tuple = ()) -> Optional[List[Any]]:
        # Ejecuta una consulta SQL que retorna resultados (SELECT)
        # y retorna una lista con los resultados
        try:
            self.cursor.execute(query, params)
            resultados = self.cursor.fetchall()
            # Convertimos cada fila en un diccionario
            result_list = [dict(row) for row in resultados]
            print("Consulta de selección ejecutada exitosamente.")
            return result_list
        except Error as e:
            print(f"Error al ejecutar la consulta de selección: {e}")
            return None

    # singleton.py  ➜ agrega este método dentro de la clase Database
    def executemany(self, query: str, seq_params: List[Tuple]) -> None:
        """
        Ejecuta la misma consulta SQL con múltiples conjuntos de parámetros
        (útil para inserciones masivas).
        """
        try:
            self.cursor.executemany(query, seq_params)
            self.connection.commit()
            print("Consulta executemany ejecutada exitosamente.")
        except Error as e:
            print(f"Error en executemany: {e}")
            self.connection.rollback()


    def close_connection(self):
        # Cerramos la conexión a la base de datos.
        if self.close_connection:
            self.connection.close()
            Database._instance = None
            print("Conexión a la base de datos cerrada")