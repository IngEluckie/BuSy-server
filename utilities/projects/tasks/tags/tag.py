# tag.py

from dataclasses import dataclass
from typing import Any

@dataclass
class Tag:
    base: str

    def __post_init__(self) -> None:
        normalized = self._normalize(self.base)
        object.__setattr__(self, "base", normalized)

    @staticmethod
    def _normalize(raw: str) -> str:
        if not isinstance(raw, str):
            raise TypeError("Tag base must be a string.")
        cleaned = raw.strip()
        if cleaned.startswith("#"):
            cleaned = cleaned[1:]
        if not cleaned:
            raise ValueError("Tag base cannot be empty.")
        return cleaned

    @property
    def name(self) -> str:
        return f"#{self.base}"

    def matches(self, raw: str) -> bool:
        return self.base == self._normalize(raw)

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Tag):
            return self.base == other.base
        if isinstance(other, str):
            return self.matches(other)
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.base)


if __name__ == "__main__":
    tag_a = Tag("juguetes")
    tag_b = Tag("#juguetes")
    tag_c = Tag("compras")

    print("tag_a:", tag_a.name)
    print("tag_b:", tag_b.name)
    print("tag_a == tag_b:", tag_a == tag_b)
    print("tag_a == 'juguetes':", tag_a == "juguetes")
    print("tag_a == '#juguetes':", tag_a == "#juguetes")

    tags = [tag_a, tag_c]
    query = "#juguetes"
    found = [t for t in tags if t.matches(query)]
    print("found:", [t.name for t in found])