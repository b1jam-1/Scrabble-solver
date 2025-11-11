import os
from flask import Blueprint, jsonify, request, send_file
import tempfile
from scrabble_solver.tile import Tile
from scrabble_solver.board import Board
from scrabble_solver.solver import Solver
from scrabble_solver.board import BONUS as BONUS_MAP
from scrabble_solver.utils import VALUES, load_dictionary, board_to_lines, save_board_to_file, load_board_from_file
from scrabble_solver.board import BOARD_SIZE

api_bp = Blueprint('api', __name__)

# Initialisation du jeu (chargement du dictionnaire, plateau, solver)
ROOT = os.path.dirname(os.path.abspath(__file__))

DICT_PATH = os.path.join(ROOT, 'mots.txt')
if not os.path.exists(DICT_PATH):
    raise SystemExit('Dictionnaire mots.txt introuvable dans le dossier du projet. Placez votre dictionnaire (un mot par ligne).')

trie, words = load_dictionary(DICT_PATH)
board = Board()
solver = Solver(board, trie, words)
cached_moves = [] # Stocke les coups calculés par le solver


# --- Routes API ---

@api_bp.route('/board/upload', methods=['POST'])
def api_board_upload():
    """Charge un plateau depuis un fichier .txt envoyé par le frontend."""

    # Vérification de la présence du fichier
    if 'file' not in request.files:
        return jsonify({'ok': False, 'error': 'Aucun fichier envoyé'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'ok': False, 'error': 'Nom de fichier vide'}), 400
    
    # Sauvegarde temporaire du fichier et chargement du plateau car load_board_from_file nécessite un chemin de fichier
    with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as tmp:
        file.save(tmp.name)
        try:
            load_board_from_file(board, tmp.name)
        except Exception as e:
            return jsonify({'ok': False, 'error': f'Erreur lors du chargement: {e}'}), 400

    return jsonify({'ok': True, 'lines': board_to_lines(board)})

@api_bp.route('/board/download', methods=['GET'])
def api_board_download():
    """Permet de télécharger le plateau actuel au format .txt."""
    # Création d'un fichier temporaire pour stocker le plateau car Flask send_file nécessite un fichier physique
    with tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w', encoding='utf-8') as tmp:
        save_board_to_file(board, tmp.name)
        tmp.flush()
        path = tmp.name

    return send_file(path, as_attachment=True, download_name='plateau.txt', mimetype='text/plain')

@api_bp.route('/board', methods=['GET'])
def api_board():
    """Renvoie l'état actuel du plateau sous forme de lignes."""
    return jsonify({'lines': board_to_lines(board)})

@api_bp.route('/meta', methods=['GET'])
def api_meta():
    """Renvoie les métadonnées du jeu (bonus, valeurs des lettres, taille du plateau)."""
    bonus_map = {f"{r},{c}": b for (r, c), b in BONUS_MAP.items()}
    return jsonify({'bonus': bonus_map, 'values': VALUES, 'board_size': BOARD_SIZE})

@api_bp.route('/set_cell', methods=['POST'])
def api_set_cell():
    """Met à jour une cellule du plateau (on met une tuile ou on vide la case)."""
    data = request.json or {}
    try:
        r = int(data.get('r'))
        c = int(data.get('c'))
        ch = data.get('ch', '')
        is_blank = bool(data.get('is_blank', False))
        if not ch:
            board.set(r, c, None)
        else:
            tile = Tile(letter=str(ch).upper(), is_blank=is_blank)
            board.set(r, c, tile)
        return jsonify({'ok': True, 'lines': board_to_lines(board)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

@api_bp.route('/moves', methods=['GET'])
def api_moves():
    """Renvoie les meilleurs coups possibles"""
    try:
        topk = int(request.args.get('topk', 10))
    except Exception:
        topk = 10
    rack = request.args.get('rack', '')
    moves = solver.best_moves(rack, top_k=topk)
    global cached_moves
    cached_moves = moves
    out = []
    for idx, m in enumerate(moves):
        total, breakdown = solver.score_move(m.direction, m.placements)
        out.append({
            'idx': idx,
            'score': m.score,
            'word': m.word,
            'row': m.row,
            'col': m.col,
            'direction': m.direction,
            'placements': m.placements,
            'breakdown': breakdown,
        })
    return jsonify({'moves': out})

@api_bp.route('/apply_move', methods=['POST'])
def api_apply_move():
    """Applique un coup sur le plateau, soit à partir d'un index dans les coups calculés,
    soit à partir d'un ensemble de placements donnés."""
    data = request.json or {}
    idx = data.get('idx')
    if idx is not None:
        try:
            idx = int(idx)
            mv = cached_moves[idx]
            solver.apply_move(mv)
            return jsonify({'ok': True, 'lines': board_to_lines(board), 'placements': mv.placements})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 400
    placements = data.get('placements')
    if not placements:
        return jsonify({'ok': False, 'error': 'placements manquants'}), 400
    placements = [(int(r), int(c), str(ch), bool(is_blank)) for (r, c, ch, is_blank) in placements]
    solver.apply_placements(placements)
    return jsonify({'ok': True, 'lines': board_to_lines(board), 'placements': placements})

@api_bp.route('/clear', methods=['POST'])
def api_clear():
    """Vide le plateau de Scrabble (remet toutes les cases à None)."""
    board.clear()
    return jsonify({'ok': True, 'lines': board_to_lines(board)})
