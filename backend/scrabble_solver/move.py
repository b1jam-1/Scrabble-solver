from typing import List
from .utils import Placement


class Move:
    """Représente un coup jouable sur le plateau."""
    def __init__(self, score: int, word: str, row: int, col: int, direction: str, placements: List[Placement]):
        self.score: int = score
        self.word: str = word
        self.row: int = row
        self.col: int = col
        self.direction: str = direction
        self.placements: List[Placement] = placements

    def __str__(self):
        return f"{self.word} @ ({self.row},{self.col}) {self.direction} -> {self.score}"