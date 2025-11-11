from typing import Dict, List, Tuple, Set
from .board import Board, Tile, BOARD_SIZE
from .trie import Trie
import unicodedata # pour la normalisation des chaînes

# Valeurs des lettres
VALUES: Dict[str, int] = {
    "A":1, "B":3, "C":3, "D":2, "E":1, "F":4, "G":2, "H":4, "I":1,
    "J":8, "K":10, "L":1, "M":2, "N":1, "O":1, "P":3, "Q":8, "R":1,
    "S":1, "T":1, "U":1, "V":4, "W":10, "X":10, "Y":10, "Z":10
}

# Alias de type pour rendre les annotations plus lisibles
Placement = Tuple[int, int, str, bool]  # (row, col, letter, is_blank) is_blank indique si c'est un joker

DIRS = { 'H': (0,1), 'V': (1,0) }

# Caractère utilisé pour représenter un joker/blanc dans le rack
BLANK_CHAR = '?'

def letter_value(letter: str, is_blank: bool) -> int:
    """ Retourne la valeur de base de la lettre, 0 pour les jokers ou lettres inconnues."""
    if is_blank:
        return 0
    if not letter:
        return 0
    return VALUES.get(letter.upper(), 0)


def board_to_lines(board: Board) -> List[str]:
    """ Convertit le plateau en une liste de chaînes de caractères, une par ligne.
    Les cases vides sont représentées par des '.', les lettres normales en majuscules, les jokers en minuscules.
    """
    lines: List[str] = []
    for r in range(BOARD_SIZE):
        line_chars = []
        for c in range(BOARD_SIZE):
            t = board.get(r, c)
            if t is None:
                line_chars.append('.')
            else:
                letter = t.letter
                line_chars.append(letter.lower() if t.is_blank else letter) #jokers en minuscules
        lines.append("".join(line_chars))
    return lines


def save_board_to_file(board: Board, path: str) -> None:
    """ Sauvegarde le plateau dans un fichier texte.
    Les cases vides sont représentées par des '.', les lettres normales en majuscules, les jokers en minuscules.
    """
    lines = board_to_lines(board)
    with open(path, 'w', encoding='utf-8') as f:
        for ln in lines:
            f.write(ln + "\n")


def load_board_from_file(board: Board, path: str) -> None:
    """ Charge le plateau depuis un fichier texte.
    Les cases vides sont représentées par des '.', les lettres normales en majuscules, les jokers en minuscules.
    """

    with open(path, 'r', encoding='utf-8') as f:
        raw_lines = [ln.rstrip("\n") for ln in f.readlines()]

    if len(raw_lines) != BOARD_SIZE:
        raise ValueError(f"Le fichier contient {len(raw_lines)} lignes, attendu {BOARD_SIZE}.")
    
    lines = []
    # On nettoie les lignes et vérifie qu'il y'a le bon nombre de caractères par ligne
    for i in range(BOARD_SIZE):
        s = "".join(ch for ch in raw_lines[i] if not ch.isspace())
        if len(s) != BOARD_SIZE:
            raise ValueError(f"Ligne {i+1}: {len(s)} caractères, attendu {BOARD_SIZE}.")
        lines.append(s)

    # On remplit le plateau
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            ch = lines[r][c]
            if ch in ".-": # Case vide
                board.set(r, c, None)

            elif ch.isalpha():
                # On normalise la lettre (on enlève accents et on met en majuscule)
                letter = normalize_word(ch)
                is_blank = ch.islower() # jokers en minuscules
                # On vérifie que la lettre est valide
                if len(letter) != 1 or letter not in VALUES:
                    raise ValueError(f"Ligne {r+1}, colonne {c+1}: lettre invalide '{ch}'.")
                
                board.set(r, c, Tile(letter, is_blank)) # On place la tuile sur le plateau
                board.first_move_done = True # Si on charge un plateau avec des lettres, le premier coup a été joué

            else:
                raise ValueError(f"Ligne {r+1}, colonne {c+1}: caractère invalide '{ch}'.")


def normalize_word(word: str) -> str:
    """Normalise un mot en enlevant accents et tous les caractères qui ne sont pas des lettres et met les lettres en majuscules."""
    norm = unicodedata.normalize('NFD', word) # décompose les caractères accentués (é devient e´)
    filtered = ''.join(ch.upper() for ch in norm if unicodedata.category(ch) != 'Mn') # on enlève les marques d'accent et met en majuscules
    w = ""
    for ch in filtered:
        if 'A' <= ch <= 'Z':
            w += ch
    return w


def load_dictionary(path: str) -> Tuple[Trie, Set[str]]:
    """Charge le fichier de mots et retourne (trie, set_de_mots)."""
    trie = Trie()
    words: Set[str] = set()
    
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            raw = line.strip() # enlève espaces et saut de ligne
            if not raw: # si la ligne est vide, on passe à la suivante
                continue

            w = normalize_word(raw)
            if len(w) >= 2:
                words.add(w)
                trie.insert(w)

        return trie, words