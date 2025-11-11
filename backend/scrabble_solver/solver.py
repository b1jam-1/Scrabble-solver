from typing import Dict, List, Set, Tuple # Pour pouvoir spécifier des types avec des annotations
from collections import Counter # Pour gérer le rack de tuiles

# Importations des autres modules du projet
from .move import Move
from .board import Board, BONUS, BOARD_SIZE, CENTER, Tile
from .trie import Trie, TrieNode
from .utils import VALUES, letter_value, BLANK_CHAR, Placement, DIRS

class Solver:
    """Classe principale pour générer des coups candidats sur un plateau de Scrabble donné"""
    def __init__(self, board: Board, trie: Trie, dictionary: Set[str]):
        self.board = board # plateau courant
        self.trie = trie # trie des mots valides
        self.dictionary: Set[str] = dictionary # ensemble des mots valides
        self.cross_sets: Dict[Tuple[int,int,str], Set[str]] = {} # (r,c,dir) -> set de lettres autorisées pour une case et une direction
        self.candidates: List[Move] = [] # liste des coups candidats générés

    def anchors(self) -> List[Tuple[int,int]]:
        """Retourne la liste des cases 'ancre'. Ce sont les cases vides adjacentes à au moins une tuile existante.
        Sur un plateau vide, l'ancre est la case centrale.
        Les ancres sont des points de départ utilisés pour générer des coups candidats.
        """
        anchors = []
        if self.board.is_empty():
            anchors.append(CENTER)
        else:
            #on parcourt toutes les cases
            for r in range(BOARD_SIZE):
                for c in range(BOARD_SIZE):
                    if self.board.get(r,c) is None: #la case est vide
                        adj = False
                        #on regarde si il y'a au moins une tuile adjacente
                        for r_adj, c_adj in [(r-1,c),(r+1,c),(r,c-1),(r,c+1)]:
                            if self.board.in_bounds(r_adj,c_adj) and self.board.get(r_adj,c_adj) is not None:
                                adj = True
                                break
                        if adj:
                            anchors.append((r,c))
        return anchors
    
    def formed_word(self, r:int, c:int, letter:str, dr:int, dc:int) -> str:
        """Retourne le mot créé en insérant la lettre en (r,c)
        et en lisant dans la direction (dr,dc). dr et dc doivent être 0 ou ±1 et non tous les deux 0.
        """
        # On recule jusqu'au début du mot
        i, j = r, c
        while self.board.in_bounds(i - dr, j - dc) and self.board.get(i - dr, j - dc) is not None:
            i -= dr
            j -= dc

        # On avance en collectant les lettres
        word = ""
        while self.board.in_bounds(i, j):
            if i == r and j == c:
                word += letter
            else:
                t = self.board.get(i, j)
                if t is None: # Si on arrive sur une case vide le mot est fini on arrete
                    break
                word += t.letter
            i += dr
            j += dc

        return word

    def compute_cross_sets(self, anchors: List[Tuple[int,int]]):
        """Construit une map des lettres autorisées pour chaque case ancre
        (car si on y place une lettre, ça formerait un mot croisé)
    
        Les clefs sont (ligne, colonne, direction) où direction est 'H' ou 'V'.
        L'ensemble associé contient les lettres qui, placées sur cette case,
        forment un mot valide dans la direction perpendiculaire.
        """
        self.cross_sets.clear() # on réinitialise la map

        # On parcourt toutes les cases vides
        for r, c in anchors:
            # Pour la direction horizontale on va regarder si on peut former un mot vertical et inversement
            # Ce qui explique pourquoi dr=1, dc=0 dans le premier tuple et dr=0, dc=1 dans le second
            for (dr,dc,dir_char) in [(1,0,'H'),(0,1,'V')]:
                # Si la case n'est pas adjacente à une tuile dans la direction perpendiculaire,
                # il n'y a pas de contrainte de mot croisé -> on marque None pour indiquer "pas de cross-set".
                before = (r - dr, c - dc)
                after = (r + dr, c + dc)
                if not (self.board.in_bounds(before[0], before[1]) and self.board.get(before[0], before[1]) is not None) and \
                   not (self.board.in_bounds(after[0], after[1]) and self.board.get(after[0], after[1]) is not None):
                    self.cross_sets[(r, c, dir_char)] = None
                    continue

                # On récupère les lettres qui forment un mot valide (il y a au moins une tuile perpendiculaire)
                allowed = set()
                for letter in VALUES.keys(): # on essaie chaque lettre possible
                    formed = self.formed_word(r, c, letter, dr, dc)
                    if len(formed) > 1 and formed in self.dictionary:
                        allowed.add(letter)

                # Si aucune lettre ne forme un mot valide, allowed restera vide -> cela interdit toute lettre
                self.cross_sets[(r,c,dir_char)] = allowed

    def build_prefix_string(self, built_prefix: List[Placement], existing_prefix: str, direction: str) -> str:
        """Retourne le préfixe sous forme de chaîne de caractères
        Le préfixe est composé des tuiles du built_prefix suivi de existing_prefix.
        """
        # Si il n'y a pas de built_prefix, on retourne simplement existing_prefix
        if not built_prefix:
            return existing_prefix

        # On "convertit" built_prefix en une chaîne de caractères dans la bonne direction
        if direction == 'H':
            ordered = sorted(built_prefix, key=lambda x: x[1]) # tri par colonne
        else:
            ordered = sorted(built_prefix, key=lambda x: x[0]) # tri par ligne
        placed_prefix = "".join(letter for _, _, letter, _ in ordered) # conversion en chaîne

        return placed_prefix + existing_prefix

    def extend_prefix(self, r:int, c:int, node:TrieNode, rack:Counter, direction:str, placed:List[Tuple[int,int,str,bool]]):
        """Prolonge le préfixe courant dans la direction donnée (sens du mot),
        en essayant récursivement de poser des tuiles depuis le rack et en
        collectant les mots valides formés.

        Cette fonction utilise le trie pour élaguer les continuations
        impossibles et respecte les contraintes issues des cross-sets pour
        chaque case vide.

        Placed nous permet d'avoir l'état du plateau avec les tuiles qu'on envisage de poser
        sans écrire sur la Board.
        """

        dr, dc = DIRS[direction]
        pos_r, pos_c = r, c
        current_node = node

        # On crée un dictionnaire pour accéder facilement et rapidement aux placements prévus
        placed_map = {(pr,pc):(letter,is_blank) for (pr,pc,letter,is_blank) in placed}

        while self.board.in_bounds(pos_r, pos_c):

            placed_entry = placed_map.get((pos_r, pos_c))

            if placed_entry is not None: # un placement est à cet endroit

                letter = placed_entry[0] # on récupère la lettre à poser
                child = current_node.children.get(letter) # on cherche le noeud enfant correspondant à cette lettre

                if child is None: # aucun mot ne commence par ce préfixe, on arrête la recherche
                    return
                
                # Si au moins un mot commence par ce préfixe, on avance d'une case
                # (On continue avec le noeud enfant)
                current_node = child
                pos_r += dr
                pos_c += dc
                continue
            
            # Pas de placement pour cette case
            existing = self.board.get(pos_r, pos_c)

            if existing is not None: # case déjà occupée par une tuile sur le plateau
                letter = existing.letter
                child = current_node.children.get(letter) # on cherche le noeud enfant correspondant à cette lettre depuis le préfixe courant

                if child is None: # le préfixe courant ne peut pas être suivi par la lettre de la tuile
                    return
                
                current_node = child
                pos_r += dr
                pos_c += dc
                continue

            # Pas de placement prévu pour la case actuelle ni de tuile à cet endroit

            # On regarde si on a formé un mot
            if current_node.end and placed:
                # Si le mot formé est valide et qu'on a posé au moins une lettre
                move = self.finalize_move_from_placements(direction, placed)
                if move is not None:
                    self.candidates.append(move)


            # On essaie de poser chaque lettre du rack sur cette case vide
            # on récupère les lettres autorisées pour cette case depuis le cross-set
            allowed_cross = self.cross_sets.get((pos_r, pos_c, direction) )

            for letter in list(rack.keys()):
                if rack[letter] == 0: # On a épuisé cette lettre dans le rack, on l'ignore
                    continue

                if letter == BLANK_CHAR:
                    # Si c'est un joker on doit essayer toutes les lettres possibles
                    # Qui sont dans les enfants du noeud courant (pour être sur qu'un mot commence par ce préfixe)
                    for child_letter in current_node.children.keys():

                        # Si la case est collée à une tuile existante, on vérifie si la lettre créé bien un mot "croisé" valide
                        if allowed_cross is not None and child_letter not in allowed_cross:
                            continue

                        # On pose la lettre en faisant un appel récursif
                        rack[BLANK_CHAR] -= 1
                        placed.append((pos_r, pos_c, child_letter, True))
                        self.extend_prefix(pos_r + dr, pos_c + dc, current_node.children[child_letter], rack, direction, placed)
                        # Une fois qu'on a essayé de générer tous les mots possibles avec cette lettre à cet endroit,
                        # # on retire la lettre et on restaure le rack
                        placed.pop()
                        rack[BLANK_CHAR] += 1

                else: # lettre "normale"
                    child = current_node.children.get(letter)

                    if child is None: # aucun mot ne commence par ce préfixe, on ignore cette lettre
                        continue

                    # Si la case est collée à une tuile existante, on vérifie si la lettre créé bien un mot "croisé" valide
                    if allowed_cross is not None and letter not in allowed_cross:
                        continue

                    # Si tout est bon on pose la lettre en faisant un appel récursif
                    rack[letter] -= 1
                    placed.append((pos_r, pos_c, letter, False))
                    self.extend_prefix(pos_r + dr, pos_c + dc, child, rack, direction, placed)
                    # Une fois qu'on a essayé de générer tous les mots possibles avec cette lettre à cet endroit,
                    # on retire la lettre et on restaure le rack
                    placed.pop()
                    rack[letter] += 1
            return
        
        if current_node.end and placed: #on a atteint le bout de la ligne/colonne et formé un mot
            move = self.finalize_move_from_placements(direction, placed)
            if move is not None:
                self.candidates.append(move)

    def generate_moves_from_anchor(self, anchor_r: int, anchor_c: int,
                     remaining: int, built_prefix: List[Tuple[int,int,str,bool]],
                     rack: Counter, existing_prefix: str, direction: str):
        """
        Génère récursivement tous les mots possibles à partir d'une ancre et avec le rack donné.
        On construit des préfixes avant l'ancre et pour chaque préfixe on essaie de prolonger le préfixe à l'aide du trie.

        Paramètres :
            anchor_r/anchor_c : coordonnées de l'ancre (où sera appellée extend_prefix)
            remaining : nombre de cases vides restantes avant l'ancre (où on peut poser des tuiles).
            built_prefix : liste mutable des placements en cours (sera modifiée en backtracking).
            rack : Counter des tuiles disponibles (muté et restauré pendant le backtracking).
            existing_prefix : préfixe fixe déjà présent juste avant l'ancre (lettres déjà sur le plateau).
            direction : 'H' ou 'V' (utile pour récupérer les cross_sets).

        Retourne rien, les coups valides sont ajoutés à self.candidates.
        """
        trie = self.trie # pour simplifier les appels

        # On construit le préfixe courant (built_prefix + existing_prefix) sous forme de chaîne de caractères
        prefix = self.build_prefix_string(built_prefix, existing_prefix, direction)

        # Si il y'a un préfixe, on récupère le noeud correspondant au dernier caractère du préfixe dans le trie
        # Sinon on prend la racine du trie
        node = trie.get_node(prefix) if prefix else trie.root

        if node is None: # aucun mot ne commence par ce préfixe on ne va pas plus loin
            return

        # On teste les extensions du préfixe courant
        self.extend_prefix(anchor_r, anchor_c, node, rack, direction, built_prefix)

        if remaining > 0: # Si il reste au moins une case vide avant l'ancre
            # On va faire une récursion en décalant l'ancre d'une case vers l'arrière (avant l'ancre actuelle)
            dr, dc = DIRS[direction]
            pos_r, pos_c = anchor_r - dr, anchor_c - dc

            allowed_cross = self.cross_sets.get((pos_r, pos_c, direction)) # ensemble des lettres autorisées pour la case en pos_r, pos_c

            # On essaie de poser chaque lettre du rack sur cette case vide
            for letter in list(rack.keys()):

                if rack[letter] == 0:
                    continue

                if letter == BLANK_CHAR:
                    # Si c'est un joker on doit essayer toutes les lettres possibles
                    for real_letter in VALUES.keys():
                        # On vérifie les contraintes de du cross-set
                        if allowed_cross is not None and real_letter not in allowed_cross:
                            continue
                        # On vérifie si le préfixe avec cette lettre est valide dans le trie
                        if not self.trie.has_prefix(real_letter + prefix):
                            continue
                        
                        # On pose la lettre en faisant un appel récursif
                        rack[BLANK_CHAR] -= 1
                        # On récupère are le noeud enfant correspondant au nouveau préfixe
                        child_node = node.children.get(real_letter)
                        built_prefix.append((pos_r, pos_c, real_letter, True))
                        # On essaie d'étendre le préfixe
                        if child_node is not None:
                            self.extend_prefix(anchor_r, anchor_c, child_node, rack, direction, built_prefix)
                        # On continue la récursion vers l'arrière (préfixe plus long)
                        self.generate_moves_from_anchor(pos_r, pos_c, remaining-1, built_prefix, rack, existing_prefix, direction)
                        built_prefix.pop()
                        rack[BLANK_CHAR] += 1
                else:
                    # lettre "normale"
                    # On vérifie les contraintes de du cross-set
                    if allowed_cross is not None and letter not in allowed_cross:
                        continue
                    # On vérifie si le préfixe avec cette lettre est valide dans le trie
                    if not self.trie.has_prefix(letter + prefix):
                        continue
                    
                    # On récupère le noeud enfant correspondant au nouveau préfixe
                    child_node = node.children.get(letter)
                    rack[letter] -= 1
                    built_prefix.append((pos_r, pos_c, letter, False))
                    # On essaie d'étendre le préfixe
                    if child_node is not None:
                        self.extend_prefix(anchor_r, anchor_c, child_node, rack, direction, built_prefix)
                    # On continue la récursion vers l'arrière (préfixe plus long)
                    self.generate_moves_from_anchor(pos_r, pos_c, remaining-1, built_prefix, rack, existing_prefix, direction)
                    built_prefix.pop()
                    rack[letter] += 1

        # Toutes les explorations (avant et après via extend_prefix) sont faites
        # On retourne au niveau supérieur
        return
        
    def generate_moves(self, rack: Counter):
        """Génère tous les coups candidats (ajoutés à self.candidates) pour rack donné.

        L'algorithme parcourt les ancres, calcule le nombre de tuiles maximal que l'on peut poser avant l'ancre
         (limit), récupère le préfixe contigu existant avant l'ancre,
        construit récursivement des extensions avant l'ancre on puis prolonge le préfixe
        en utilisant le trie pour élaguer les préfixes impossibles.
        """

        # On récupère les ancres et on calcule les cross-sets si le premier coup a déjà été joué
        anchors = self.anchors()
        if self.board.first_move_done is True:
            self.compute_cross_sets(anchors)
        else:
            self.cross_sets.clear()


        for direction in ["H", "V"]:

            dr, dc = DIRS[direction]

            for r, c in anchors:
                pr, pc = r - dr, c - dc # position de la case avant l'ancre par rapport à la direction courante
                limit = 0 # nombre de tuiles vides contigus avant l'ancre
                existing_prefix = "" #préfixe déjà présent avant l'ancre

                if self.board.in_bounds(pr, pc): #si la case d'avant est dans le plateau

                    if self.board.get(pr, pc) is None:
                        # Si la case d'avant est vide
                        # on calcule combien de tuiles on peut poser avant l'ancre au maximum
                        while self.board.in_bounds(pr, pc) and self.board.get(pr, pc) is None:
                            # On recule tant qu'on est dans la grille et sur une case vide
                            limit += 1
                            pr -= dr
                            pc -= dc

                    else: #Si la case d'avant n'est pas vide, on récupère le préfixe existant avant l'ancre
                        while self.board.in_bounds(pr, pc) and self.board.get(pr, pc) is not None:
                            # On recule tant qu'on est dans la grille et sur une case occupée
                            # et on construit le préfixe en ajoutant les lettres au début
                            existing_prefix = self.board.get(pr, pc).letter + existing_prefix
                            pr -= dr
                            pc -= dc

                # On peut maintenant générer des mots en posant jusqu'à limit tuiles avant l'ancre, en respectant le préfixe existant
                # Et en prolongeant le préfixe à l'aide du trie
                self.generate_moves_from_anchor(r, c, limit, [], rack.copy(), existing_prefix, direction)    

    def finalize_move_from_placements(self, direction:str, placements:List[Placement])-> Tuple[Move|None]:
        """À partir d'une liste de placements, valide le
        mot principal et les mots croisés formés, vérifie les règles du
        premier coup, puis calcule le score total. Retourne un Move ou None.
        """
        
        dr, dc = DIRS[direction]
        positions = {(r,c) for (r,c,_,_) in placements} # ensemble des positions où on place une tuile

        # On reconstitue le mot que l'on souhaite jouer
        min_r, min_c = min(placements, key=lambda x: (x[0], x[1]))[0], min(placements, key=lambda x: (x[0], x[1]))[1]
        r, c = min_r, min_c

        # On recule jusqu'au début du mot (au cas où on a un préfixe déjà sur le plateau)
        while self.board.in_bounds(r - dr, c - dc) and (self.board.get(r - dr, c - dc) is not None):
            r -= dr
            c -= dc

        # On avance en collectant les lettres du mot principal
        word_letters = []
        start_r, start_c = r, c
        while self.board.in_bounds(r, c):
            t = self.board.get(r, c)
            if t is None and (r,c) not in positions: # case vide sans placement prévu
                break # fin du mot principal

            if t is not None: # case occupée par une tuile sur le plateau
                word_letters.append(t.letter)

            else: # case où on place une tuile
                for (pr, pc, letter, is_blank) in placements:
                    if pr == r and pc == c:
                        word_letters.append(letter)
                        break
            r += dr
            c += dc

        main_word = "".join(word_letters)
        # On vérifie que le mot est valide (longueur >=2 et dans le dictionnaire)
        if len(main_word) < 2 or main_word not in self.dictionary:
            return None


        # Si c'est le premier coup, le mot doit passer par le centre
        if self.board.is_empty():
            cr, cc = CENTER
            if direction == 'H':
                # On doit être sur la même ligne et le centre doit être entre les colonnes de début et de fin du mot
                if start_r != cr or not (start_c <= cc <= start_c + len(main_word) - 1):
                    return None
            else:
                if start_c != cc or not (start_r <= cr <= start_r + len(main_word) - 1):
                    return None
                
        else:
            # Au moins un coup a été joué auparavant
            # On doit vérifier que le coup se "connecte" au plateau
            # On accepte le coup si :
            #  - le mot principal recouvre au moins une tuile déjà présente sur le plateau (overlap)
            #  - ou bien au moins une des tuiles posées est adjacente à une tuile existante

            # Vérifier recouvrement (overlap)
            overlaps = False
            # On parcourt du début à la fin les cases du mot formé
            for i in range(len(main_word)):
                rr = start_r + dr * i
                cc = start_c + dc * i
                if self.board.in_bounds(rr, cc) and self.board.get(rr, cc) is not None:
                    # Si on trouve une tuile existante sur le plateau
                    overlaps = True
                    break

            touches = overlaps
            # Si pas de recouvrement, vérifier adjacence des tuiles posées
            if not touches:
                # On parcourt toutes les tuiles posées
                for r0, c0, _, _ in placements:
                    # On regarde les 4 cases adjacentes
                    for rr, cc in [(r0-1, c0), (r0+1, c0), (r0, c0-1), (r0, c0+1)]:
                        # Si une case adjacente contient une tuile existante, on valide le coup
                        if self.board.in_bounds(rr, cc) and self.board.get(rr, cc) is not None:
                            touches = True
                            break
                    if touches:
                        break

            if not touches:
                # Rejeter le coup qui ne se connecte pas au plateau
                return None

        # Le coup est valide, on calcule le score total
        score, _ = self.score_move(direction, placements)
        return Move(score=score, word=main_word, row=start_r, col=start_c, direction=direction, placements=placements.copy())
  
    def score_move(self, direction: str, placements: List[Placement]) -> Tuple[int, Dict]:
        """Retourne (total, breakdown) où breakdown est un dict décrivant
        le mot principal, la contribution par lettre et les mots croisés formés.
        """
        dr, dc = DIRS[direction]
        # On crée un dictionnaire pour accéder facilement et rapidement aux placements prévus
        placed_set = {(r,c): (ch,is_blank) for (r,c,ch,is_blank) in placements}
        all_positions = list(placed_set.keys())
        
        # On récupère la position de début de nos placements
        r, c = min(all_positions, key=lambda p: (p[0], p[1]))
        # Si il y'a un préfixe déjà sur le plateau, on recule jusqu'au début du mot
        while self.board.in_bounds(r - dr, c - dc) and self.board.get(r - dr, c - dc) is not None:
            r -= dr
            c -= dc

        # On calcule le score du mot posé
        word_mult = 1
        total = 0
        letters_main = []
        pr, pc = r, c

        while self.board.in_bounds(pr, pc):
            t = self.board.get(pr, pc)

            if t is None and (pr,pc) not in placed_set:
                # fin du mot
                break

            if t is not None: # case occupée par une tuile sur le plateau
                total += letter_value(t.letter, t.is_blank)
                letters_main.append(t.letter)

            else: # case où on place une tuile
                letter, is_blank = placed_set[(pr,pc)]
                base = letter_value(letter, is_blank)
                b = BONUS.get((pr,pc))
                letter_score = base
                if b == "2L":
                    letter_score = base * 2
                elif b == "3L":
                    letter_score = base * 3
                total += letter_score
                if b == "2W":
                    word_mult *= 2
                elif b == "3W":
                    word_mult *= 3
                letters_main.append(letter)
            # On avance à la case suivante
            pr += dr
            pc += dc

        total *= word_mult

        breakdown = {
            'main_word': ''.join(letters_main),
            'main_word_score': total,
            'word_multiplier': word_mult,
            'placed_tiles': [],
            'cross_words': [],
            'bingo': False,
        }

        # Maintenant on calcule les scores des mots croisés formés
        pdr, pdc = dc, dr # directions perpendiculaires
        # On parcourt chaque tuile posée et on regarde si elle forme un mot croisé
        for (r0,c0),(letter,is_blank) in placed_set.items():
            base = letter_value(letter, is_blank)
            b = BONUS.get((r0,c0))
            breakdown['placed_tiles'].append({'pos': (r0,c0), 'letter': letter, 'is_blank': is_blank, 'base': base, 'bonus': b})

            before_r, before_c = r0 - pdr, c0 - pdc
            after_r, after_c = r0 + pdr, c0 + pdc
            if (self.board.in_bounds(before_r, before_c) and self.board.get(before_r, before_c) is not None) or \
               (self.board.in_bounds(after_r, after_c) and self.board.get(after_r, after_c) is not None):
                # Si on a une tuile avant ou après dans la direction perpendiculaire,
                # on construit le mot croisé
                i, j = r0, c0
                # On recule jusqu'au début du mot croisé
                while self.board.in_bounds(i - pdr, j - pdc) and self.board.get(i - pdr, j - pdc) is not None:
                    i -= pdr
                    j -= pdc
                # On avance en collectant les valeurs des lettres du mot croisé
                cross_score = 0
                cross_mult = 1
                cross_letters = []
                while self.board.in_bounds(i, j):
                    if i == r0 and j == c0:
                        # Si c'est la lettre que l'on vient de poser (qui fait aussi parti du mot principal)
                        # On recompte sa valeur et sont bonus éventuel
                        b = BONUS.get((i,j))
                        if b == "2L":
                            cross_score += base * 2
                        elif b == "3L":
                            cross_score += base * 3
                        if b == "2W":
                            cross_mult *= 2
                        elif b == "3W":
                            cross_mult *= 3
                        cross_score += base
                        cross_letters.append(letter)
                    else:
                        t = self.board.get(i, j)
                        if t is None: # fin du mot croisé
                            break
                        cross_letters.append(t.letter)
                        cross_score += letter_value(t.letter, t.is_blank)
                    i += pdr
                    j += pdc

                # On ajoute le score du mot croisé s'il a une longueur > 1 (on sait qu'il est valide grace au cross-set vérifié avant)
                cross_word = "".join(cross_letters)
                if len(cross_word) > 1:
                    cross_total = cross_score * cross_mult
                    breakdown['cross_words'].append({'word': cross_word, 'positions_start': (i - pdr*len(cross_letters), j - pdc*len(cross_letters)), 'score': cross_total})
                    total += cross_total

        # Bonus 'bingo' pour utilisation de 7 tuiles
        if len(placements) == 7:
            total += 50
            breakdown['bingo'] = True

        return total, breakdown

    def best_moves(self, rack_str: str, top_k:int=1) -> List[Move]:
        """Retourne les top_k meilleurs coups pour le rack donné"""
        rack = Counter(ch.upper() for ch in rack_str if ch.strip()) # Nettoyage du rack et mise en majuscules
        self.candidates = []
        self.generate_moves(rack.copy()) # .copy() pour ne pas modifier le rack original
        self.candidates.sort(key=lambda m: (-m.score, m.word, m.row, m.col, m.direction)) # Tri par score décroissant, puis par ordre alphabétique et position
        return self.candidates[:top_k]

    def apply_placements(self, placements: List[Placement]):
        """Applique une liste de placements sur le plateau"""
        for r,c,ch,is_blank in placements:
            self.board.set(r,c, Tile(ch, is_blank))
        self.board.first_move_done = True
        
    def apply_move(self, move: Move):
        """Applique le coup donné sur le plateau"""
        self.apply_placements(move.placements)