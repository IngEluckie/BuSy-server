# fileManager.py

"""
¿QUÉ HACE?
"""

# Importamos librerías
# Importamos módulos

from fastapi import UploadFile
from pathlib import Path
from pydantic import BaseModel
import os
from io import BytesIO
#import threading
from typing import Tuple


class FileManager:
    """
    Clase padre encargada de gestionar:
    - Tipo de archivo
    - Ubicación
    ...
    """

    _ALLOWED_FORMATS: Tuple[str, ...] = (
        ".jpg", ".jpeg", ".png", ".pdf",
        ".mp4", ".webm", ".zip", ".rar",
        ".docx", ".xlsx", ".pptx"
    )

    def __init__(self, file_path: str) -> None:
        self._base_path: str = os.path.dirname(__file__)
        self._folder_path: str = self._ensure_folder(file_path)

    def _ensure_folder(self, folder_relative: str) -> str:
        folder = os.path.join(self._base_path, folder_relative)
        os.makedirs(folder, exist_ok=True)  # Crea el directorio si no existe
        return folder
    
    # ----------------------  API PÚBLICA --------------------
    @property
    def allowed_formats(self) -> Tuple[str, ...]:
        return self._ALLOWED_FORMATS
    
    def saveFile(self):
        pass

    def getFile(self):
        pass

    def getFiles(self):
        return []






    """
    Testing
    """
    def test1() -> None:
        pass

    if __name__ == "__main__":
        pass