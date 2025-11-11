# Scrabble Solver

Solveur Scrabble complet en Python avec interface web (Flask + JavaScript) et moteur de recherche de coups ultra-rapide (TRIE, cross-sets).

Toutes les fonctionnalités sont également accessibles via une API REST documentée, idéale pour l’intégration, l’automatisation ou l’utilisation avancée (voir section [API REST](#api-rest)).

<img width="2750" height="1392" alt="illustration" src="https://github.com/user-attachments/assets/5452be37-cd99-44d2-bcad-0ef55209040a" />

---

## Sommaire

- [Fonctionnalités](#fonctionnalités)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Lancement](#lancement)
- [Utilisation via l'interface web](#interface-web)
- [Utilisation via l'API REST](#api-rest)
- [API Python](#api-python)
- [Structure du projet](#structure-du-projet)

---

## Fonctionnalités

- Grille 15×15 avec bonus officiels (lettre/mot x2, x3)
- Recherche des meilleurs coups (validation croisée, score, jokers)
- Interface web
- Visualisation et application des coups en un clic
- Import/export de grilles
- API REST pour intégration ou usage avancé

---

## Prérequis

- Python 3.9+
- Un fichier de dictionnaire `mots.txt` (un mot par ligne, format texte)
> Il est conseillé d'utiliser le dictionnaire ODS (Officiel du Scrabble) pour que les mots reconnus correspondent aux règles du jeu. L'ODS est la référence officielle et est soumis à licence : procurez‑vous une copie autorisée ou utilisez une wordlist personnelle.

---

## Installation

1. Clonez ce dépôt et placez `mots.txt` dans le dossier `backend/`.

2. Installez les dépendances Python : ![Flask](https://img.shields.io/badge/Flask-2.0%2B-blue?logo=flask)

```bash
cd backend
pip install -r requirements.txt
```

---

## Lancement

Dans le dossier `backend/` :

```bash
python main.py
```
Le navigateur s'ouvre automatiquement.
Vous pouvez également vous rendre manuellement à l'adresse [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## Utilisation

### Format des grilles

- 15 lignes, 15 caractères par ligne
- `.` ou `-` = case vide
- Majuscule = tuile normale
- Minuscule = joker placé (0 point)

Exemple de grille :
```
...............
...............
...............
...............
...............
...............
...............
....EXEMPLE....
...............
...............
...............
...............
...............
...............
...............
```

### Interface Web
Vous trouverez ici une aide pour démarrer et une explication rapide des commandes et conventions. Ces informations sont également accessibles dans une fenêtre d'aide à l'ouverture de la page web.
- **Saisie dans la grille** :
    - A–Z : tuile normale
    - a–z : joker (lettre minuscule)
    - . ou - : case vide
- **Chevalet** :
    - A–Z / a–z : tuile normale
    - ? : joker
- **Actions** :
    - Bouton « Calculer » : recherche les meilleurs coups
    - Bouton « Vider » : réinitialise la grille et le chevalet
    - Survolez un coup pour le prévisualiser, cliquez pour l’appliquer

### API REST

La section suivante détaille les principaux endpoints de l’API REST, leurs méthodes, paramètres et exemples de requêtes/réponses.

#### `GET /api/board`
Renvoie l’état actuel du plateau.

**Réponse :**
```js
{
  "lines": ["...............",...] // 15 lignes de 15 caractères
}
```

#### `GET /api/meta`
Renvoie les métadonnées du jeu (bonus, valeurs des lettres, taille du plateau).

**Réponse :**
```js
{
  "board_size": 15,
  "bonus": {"0,0":"3W","0,11":"2L", ...},
  "values": {"A": 1, "B": 3, ...}
}
```

#### `POST /api/set_cell`
Modifie une case du plateau.

**Body JSON :**
```js
{
  "r": 7,         // ligne (0-14)
  "c": 7,         // colonne (0-14)
  "ch": "A",     // lettre (ou vide pour effacer)
  "is_blank": false // optionnel, true si joker
}
```

**Exemples de réponse :**
```js
{
  "ok": true,
  "lines": [ ... ] // plateau
}
```
```js
{
  "ok": false,
  "error": "..."
}
```

#### `GET /api/moves`
Calcule les meilleurs coups possibles pour un chevalet donné.

**Paramètres query :**
- `rack` : lettres du chevalet (ex : "AEIRST?")
- `topk` : nombre de coups à retourner (optionnel, défaut : 10)

**Exemple :**
`GET /api/moves?rack=AEIRST?&topk=5`

**Réponse :**
```js
{
  "moves": [
    {
      "idx": 0,
      "score": 78,
      "word": "RATISSES",
      "row": 7,
      "col": 8,
      "direction": "V",
      "placements": [[7,8,"A",false], ...],
      "breakdown": {
            "main_word": "RATISSES",
            "main_word_score"': 78,
            "word_multiplier"': word_mult,
            "placed_tiles"': [
                {
                "pos": (7, 8),
                "letter": "R",
                "is_blank": False,
                "base": 1, // Valeur de base de la lettre
                "bonus": null // ou "3W", ...
                }, ...
                ],
            "cross_words"': [], // Les mots croisés formés s'il y'en a
            "bingo"': True // Bonus de 50 points si toutes les lettres du rack ont été posées
        }
    },
    ...
  ]
}
```

#### `POST /api/apply_move`
Applique un coup sur le plateau.

**Body JSON :**
```js
{
  "idx": 0 // index d’un coup précédemment calculé
  // ou
  "placements": [[7,7,"A",false], ...] // liste de placements manuels
}
```
**Exemples de réponse :**
```js
{
  "ok": true,
  "lines": [ ... ], // plateau
  "placements": [[7,7,"A",false], ...]
}
```
```js
{
  "ok": false,
  "error" : "..."
}
```
#### `POST /api/clear`
Vide le plateau (remet toutes les cases à None).

**Réponse :**
```js
{
  "ok": true,
  "lines": [ ... ]
}
```

#### `POST /api/board/upload`
Charge un plateau depuis un fichier texte (multipart/form-data, champ `file`).

**Réponse :**
```js
{
  "ok": true,
  "lines": [ ... ]
}
```
```js
{
"ok": false,
"error": "Aucun fichier envoyé"
}
```

#### `GET /api/board/download`
Télécharge le plateau actuel au format texte.

**Réponse :**
Fichier texte (attachment)

---

## API Python

Exemple minimal pour trouver les meilleurs coups en Python :

```python
from scrabble_solver import Board, Solver, load_dictionary

trie, words = load_dictionary("mots.txt")
board = Board()
solver = Solver(board, trie, words)

# Exemple d'utilisation
moves = solver.best_moves("AEIRST?", top_k=10)
for mv in moves:
    print(mv)
```

---

## Structure du projet

```
backend/
    main.py           # Point d’entrée Flask
    app.py, api.py    # Logique serveur/API
    mots.txt          # Dictionnaire de mots
    requirements.txt  # Dépendances Python
    scrabble_solver/
        board.py, solver.py, trie.py, ...
frontend/
    static/
        app.js, style.css
    templates/
        index.html
README.md
```

---
