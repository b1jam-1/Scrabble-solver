class Tile:
    """Représente une tuile de Scrabble avec une lettre et un indicateur de joker."""
    def __init__(self, letter: str, is_blank: bool):
        self.letter = letter
        self.is_blank = is_blank # Indique si la lettre est un joker (pas de points) ou non