from typing import List, Optional, Tuple # Pour pouvoir spécifier des types avec des annotations
from .tile import Tile

BOARD_SIZE = 15
CENTER: Tuple[int, int] = (BOARD_SIZE // 2, BOARD_SIZE // 2)

# Définition des cases bonus sur le plateau
BONUS: dict[Tuple[int, int], str] = {} #"3W" mot triple, "2W" mot double, "3L" lettre triple, "2L" lettre double

mid = CENTER[0]
last = BOARD_SIZE - 1

# On place les cases mot compte triple (3W)
for x, y in [(0,0),(0,7),(0,14),(7,0),(7,14),(14,0),(14,7),(14,14)]:
            BONUS[(x, y)] = "3W"

# On place les cases mot compte double (2W)
for x, y in [
    (1,1),(2,2),(3,3),(4,4),(7,7),(10,10),(11,11),(12,12),(13,13),
    (1,13),(2,12),(3,11),(4,10),(10,4),(11,3),(12,2),(13,1)
]:
    BONUS[(x,y)] = "2W"

# On place les cases lettre compte double (2L)
for x,y in [
    (0,3),(0,11),(2,6),(2,8),(3,0),(3,7),(3,14),(6,2),(6,6),(6,8),(6,12),
    (7,3),(7,11),(8,2),(8,6),(8,8),(8,12),(11,0),(11,7),(11,14),(12,6),(12,8),(14,3),(14,11)
]:
    BONUS[(x,y)] = "2L"

# Lettre compte triple (3L)
for x,y in [(1,5),(1,9),(5,1),(5,5),(5,9),(5,13),(9,1),(9,5),(9,9),(9,13),(13,5),(13,9)]:
    BONUS[(x,y)] = "3L"


class Board:
    """Représente le plateau de Scrabble avec une grille 15x15 de tuiles (ou None)."""
    def __init__(self):
        # On représente le plateau par une grille 2D de tuiles / None, par défaut toutes les cases sont vides (None)
        self.grid: List[List[Optional[Tile]]] = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.first_move_done = False

    def in_bounds(self, r: int, c: int) -> bool:
        """Retourne True si (r,c) est dans les limites du plateau."""
        return 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE

    def get(self, r: int, c: int) -> Optional[Tile]:
        """Retourne la tuile à la position (r,c) ou None si hors limites ou case vide."""
        if not self.in_bounds(r, c):
            return None
        return self.grid[r][c]

    def set(self, r: int, c: int, tile: Optional[Tile]):
        """Place une tuile (ou None pour vider la case) à la position (r,c) si dans les limites."""
        if self.in_bounds(r, c):
            self.grid[r][c] = tile

    def is_empty(self) -> bool:
        """Retourne True si le plateau est vide (aucune tuile posée)."""
        for row in self.grid:
            for t in row:
                if t is not None:
                    return False
        return True

    def word_at(self, r: int, c: int, dr: int, dc: int) -> str:
        """Retourne le mot continu (lettres existantes) passant par (r,c) dans la direction (dr,dc).
        dr et dc doivent être 0 ou ±1 et (dr,dc) ne peut pas être (0,0)."""
        # On retourne au début du mot
        i, j = r, c
        while self.in_bounds(i - dr, j - dc) and self.get(i - dr, j - dc) is not None:
            i -= dr
            j -= dc
        # On peut maintenant aller dans la direction indique et former le mot
        letters = []
        while self.in_bounds(i, j) and self.get(i, j) is not None:
            letters.append(self.get(i, j).letter)
            i += dr
            j += dc
        return "".join(letters)
    
    def clear(self):
        """Vide complètement le plateau (toutes les cases à None) et réinitialise l'état."""
        self.grid = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.first_move_done = False