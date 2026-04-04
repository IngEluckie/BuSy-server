from dataclasses import dataclass
from typing import List

from .product import Product


@dataclass
class Article:
    barCode: int
    folio: int
    rProduct: Product
    oPrice: int
    dPrice: int
    image: List[str]
