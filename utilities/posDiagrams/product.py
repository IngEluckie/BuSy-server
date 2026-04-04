from dataclasses import dataclass
from typing import List


@dataclass
class Product:
    id: int
    category: str  # Por el momento, no lo tengo claro
    description: str
    oPrice: int  # "original price". Int to avoid float errors
    dPrice: int  # "discount price". Same...
    image: List[str]  # File path
