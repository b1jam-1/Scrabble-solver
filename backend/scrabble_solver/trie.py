from typing import Dict, Optional # Pour pouvoir spécifier des types avec des annotations


class TrieNode:
    """Noeud d'un trie"""
    def __init__(self):
        self.children: Dict[str, 'TrieNode'] = {} # dictionnaire des enfants
        self.end: bool = False # indique si c'est la fin d'un mot


class Trie:
    """Trie minimal pour insertion et recherche par préfixe."""

    def __init__(self):
        self.root = TrieNode()

    def insert(self, word: str):
        """Insère un mot dans le trie"""
        node = self.root
        for ch in word:
            if ch not in node.children:
                node.children[ch] = TrieNode()
            node = node.children[ch]
        node.end = True # on est à la fin du mot

    def has_prefix(self, prefix: str) -> bool:
        """Retourne True si prefix est le début d'(au moins) un mot."""
        node = self.root
        for ch in prefix:
            if ch not in node.children:
                return False
            node = node.children[ch]
        return True

    def get_node(self, prefix: str) -> Optional[TrieNode]:
        """Renvoie le noeud correspondant au dernier caractère du préfixe ou None si absent."""
        node = self.root
        for ch in prefix:
            if ch not in node.children:
                return None
            node = node.children[ch]
        return node