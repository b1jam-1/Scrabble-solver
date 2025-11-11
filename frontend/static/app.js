// Appel générique à l'API backend (GET/POST)
const api = async (path, opts) => {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
};

// Variables globales pour l'état de l'application
let currentMeta = null; // Métadonnées du plateau
let selectedCell = null; // Cellule sélectionnée
let committedLines = null; // Etat du plateau validé

// Au chargement du DOM, afficher l'aide et initialiser l'UI
window.addEventListener('DOMContentLoaded', () => {
  const helpModal = new bootstrap.Modal(document.getElementById('helpModal'));
  helpModal.show();
  initScrabbleUI();
});

// Fonction principale d'initialisation de l'interface
async function initScrabbleUI() {
  try {
    currentMeta = await api('/api/meta'); // Récupère les infos du plateau
    await renderAll(); // Affiche tous les éléments
    bindUIEvents(); // Lie les événements UI
    committedLines = (await api('/api/board')).lines;
  } catch (e) {
    showError('Erreur lors du chargement des données.');
    console.error(e);
  }
}

// Affiche une erreur à l'utilisateur
function showError(msg) {
  alert(msg); // Peut être remplacé par un toast Bootstrap
}

// Fonction pour limiter la fréquence d'exécution d'une fonction
function debounce(fn, delay) {
  let timer = null;
  return function(...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}

// Lie les événements sur les éléments de l'interface
function bindUIEvents() {
  // Bouton Calculer avec debounce
  const computeBtn = document.getElementById('compute');
  const debouncedCompute = debounce(() => computeMoves(), 350);
  computeBtn.addEventListener('click', debouncedCompute);

  // Bouton pour vider la grille
  document.getElementById('clear').addEventListener('click', async () => {
    if (!confirm('Vider la grille ?')) return;
    await api('/api/clear', { method: 'POST' });
    await renderAll();
    committedLines = (await api('/api/board')).lines;
  });

  // Boutons upload/download du plateau
  const uploadBtn = document.getElementById('board-upload-btn');
  const uploadInput = document.getElementById('board-upload-file');
  const downloadBtn = document.getElementById('board-download-btn');

  if (uploadBtn && uploadInput) {
    uploadBtn.addEventListener('click', () => uploadInput.click());
    uploadInput.addEventListener('change', async (e) => {
      const file = uploadInput.files[0];
      if (!file) return;
      const formData = new FormData();
      formData.append('file', file);
      try {
        const res = await fetch('/api/board/upload', { method: 'POST', body: formData });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Erreur lors du chargement du plateau');
        await renderAll();
        committedLines = (await api('/api/board')).lines;
        alert('Plateau chargé avec succès !');
      } catch (err) {
        showError('Erreur lors du chargement du plateau : ' + err.message);
      } finally {
        uploadInput.value = '';
      }
    });
  }

  if (downloadBtn) {
    downloadBtn.addEventListener('click', async () => {
      try {
        const res = await fetch('/api/board/download');
        if (!res.ok) throw new Error('Erreur lors de la sauvegarde du plateau');
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'plateau.txt';
        document.body.appendChild(a);
        a.click();
        setTimeout(() => {
          document.body.removeChild(a);
          window.URL.revokeObjectURL(url);
        }, 100);
      } catch (err) {
        showError('Erreur lors de la sauvegarde du plateau : ' + err.message);
      }
    });
  }

  // Déclenche le calcul lors de la saisie du chevalet ou du nombre de coups à afficher
  const rackDiv = document.getElementById('rackdiv');
  const topkInput = document.getElementById('topk');
  if (rackDiv) {
    rackDiv.addEventListener('input', debounce(() => computeMoves(), 400));
  }
  if (topkInput) {
    topkInput.addEventListener('input', debounce(() => computeMoves(), 400));
    topkInput.addEventListener('input', () => {
      computeBtn.textContent = 'Calculer';
    });
  }
  // Gestion des raccourcis clavier
  document.addEventListener('keydown', globalKeyHandler);
}

// Gestionnaire de raccourcis clavier
function globalKeyHandler(e) {
  if (e.key === 'Enter') {
    const active = document.activeElement;
    if (active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA' || active.isContentEditable)) return;
    computeMoves();
  }
  if (!selectedCell) return;
  const { r, c } = selectedCell;
  // Navigation et saisie sur la grille
  if (e.key.length === 1 && /[a-zA-Z]/.test(e.key)) {
    setCell(r, c, e.key);
  } else if (e.key === 'Backspace' || e.key === 'Delete') {
    setCell(r, c, '');
  } else if (e.key === 'ArrowLeft') {
    selectCell(r, Math.max(0, c - 1));
  } else if (e.key === 'ArrowRight') {
    selectCell(r, Math.min(currentMeta.board_size - 1, c + 1));
  } else if (e.key === 'ArrowUp') {
    selectCell(Math.max(0, r - 1), c);
  } else if (e.key === 'ArrowDown') {
    selectCell(Math.min(currentMeta.board_size - 1, r + 1), c);
  }
}

// Modifie la lettre d'une cellule du plateau
async function setCell(r, c, ch) {
  const is_blank = ch === ch.toLowerCase() && ch !== '';
  await api('/api/set_cell', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ r, c, ch, is_blank })
  });
  await renderBoard();
  clearSelection();
}

// Rafraîchit tous les éléments de l'interface
async function renderAll() {
  await renderBoard();
  await renderRack();
  await renderMoves();
}

// Affiche le plateau de jeu
async function renderBoard() {
  const meta = currentMeta;
  const { lines } = await api('/api/board');
  const container = document.getElementById('board');
  container.innerHTML = '';
  container.style.gridTemplateColumns = `repeat(${meta.board_size}, var(--board-cell-size))`;
  for (let r = 0; r < lines.length; r++) {
    for (let c = 0; c < lines[r].length; c++) {
      const ch = lines[r][c] === '.' ? '' : lines[r][c];
      const el = createCellElement(r, c, ch, meta);
      container.appendChild(el);
    }
  }
}

// Crée un élément DOM pour une cellule du plateau
function createCellElement(r, c, ch, meta) {
  const el = document.createElement('div');
  el.className = 'cell';
  el.dataset.r = r;
  el.dataset.c = c;
  el.tabIndex = 0;
  el.textContent = '';
  // Affichage d'une tuile placée
  if (ch && ch !== '.') {
    const is_blank = ch === ch.toLowerCase();
    const tile = document.createElement('div');
    tile.className = 'placed-tile' + (is_blank ? ' blank' : '');
    const letspan = document.createElement('div');
    letspan.className = 'tile-letter';
    letspan.textContent = ch.toUpperCase();
    const scoreSpan = document.createElement('div');
    scoreSpan.className = 'tile-score';
    const val = meta.values?.[ch.toUpperCase()] ?? 0;
    scoreSpan.textContent = is_blank ? '' : String(val);
    tile.append(letspan, scoreSpan);
    el.appendChild(tile);
  }
  // Affichage du bonus si présent
  const key = `${r},${c}`;
  if ((!ch || ch === '.') && meta.bonus?.[key]) {
    el.classList.add('bonus-' + meta.bonus[key]);
    const lbl = document.createElement('div');
    lbl.className = 'bonus-label';
    lbl.textContent = meta.bonus[key];
    el.appendChild(lbl);
  }
  // Gestion du drag & drop sur la cellule
  el.addEventListener('dragover', e => e.preventDefault());
  el.addEventListener('drop', async (e) => {
    e.preventDefault();
    let data = e.dataTransfer.getData('text/plain');
    if (!data) return;
    let ch = '';
    let is_blank = false;
    try {
      const parsed = JSON.parse(data);
      ch = parsed.ch || '';
      is_blank = !!parsed.is_blank;
    } catch (err) {
      ch = data;
      is_blank = (ch === ch.toLowerCase() && ch !== '');
    }
    await api('/api/set_cell', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ r, c, ch, is_blank }) });
    await renderBoard();
  });
  // Sélection de la cellule au clic ou focus
  el.addEventListener('click', () => selectCell(r, c));
  el.addEventListener('focus', () => selectCell(r, c));
  return el;
}

// Sélectionne une cellule sur le plateau
function selectCell(r, c) {
  document.querySelectorAll('.cell.selected').forEach(x => x.classList.remove('selected'));
  const el = document.querySelector(`.cell[data-r='${r}'][data-c='${c}']`);
  if (el) {
    el.classList.add('selected');
    selectedCell = { r, c };
  }
}

// Désélectionne toute cellule
function clearSelection() {
  document.querySelectorAll('.cell.selected').forEach(x => x.classList.remove('selected'));
  selectedCell = null;
}

// Affiche le chevalet de l'utilisateur
async function renderRack() {
  const rackDiv = document.getElementById('rackdiv');
  rackDiv.innerHTML = '';
  const rack = [];
  for (let i = 0; i < 7; i++) {
    const wrapper = document.createElement('div');
    wrapper.className = 'rack-tile';
    const inp = document.createElement('input');
    inp.type = 'text';
    inp.maxLength = 1;
    inp.className = 'rack-input';
    inp.dataset.idx = String(i);
    inp.value = rack[i] || '';
    inp.draggable = true;
    // Permet le drag & drop d'une lettre
    inp.addEventListener('dragstart', e => {
      const payload = { ch: inp.value || '', is_blank: (inp.value === '?') };
      e.dataTransfer.setData('text/plain', JSON.stringify(payload));
    });
    // Gestion de la saisie d'une lettre
    inp.addEventListener('input', () => {
      let v = inp.value || '';
      if (v.length > 1) v = v.charAt(v.length - 1);
      if (v === '?') {
        inp.value = '?';
      } else if (/^[a-zA-Z]$/.test(v)) {
        inp.value = v.toUpperCase();
      } else {
        inp.value = '';
      }
      if (inp.value.length === 1) {
        const next = rackDiv.querySelector(`input[data-idx='${i + 1}']`);
        if (next) next.focus();
      }
    });
    // Navigation clavier sur le chevalet
    inp.addEventListener('keydown', e => {
      const prev = rackDiv.querySelector(`input[data-idx='${i - 1}']`);
      const next = rackDiv.querySelector(`input[data-idx='${i + 1}']`);
      if (e.key && e.key.length === 1 && /^[a-zA-Z?]$/.test(e.key)) {
        const curVal = inp.value || '';
        if (curVal.length === 1) {
          e.preventDefault();
          const chVal = (e.key === '?') ? '?' : e.key.toUpperCase();
          let target = null;
          for (let j = i + 1; j < 7; j++) {
            const cand = rackDiv.querySelector(`input[data-idx='${j}']`);
            if (cand && (!cand.value || cand.value.length === 0)) { target = cand; break; }
          }
          if (target) {
            target.value = chVal;
            const nextIdx = parseInt(target.dataset.idx, 10) + 1;
            const nextEl = rackDiv.querySelector(`input[data-idx='${nextIdx}']`);
            if (nextEl) nextEl.focus(); else target.focus();
          } else {
            inp.value = chVal;
          }
          return;
        }
      }
      if (e.key === 'ArrowLeft' && prev) { prev.focus(); e.preventDefault(); }
      else if (e.key === 'ArrowRight' && next) { next.focus(); e.preventDefault(); }
      else if (e.key === 'Enter') { computeMoves(); e.preventDefault(); }
      else if (e.key === 'Backspace') {
        if (!inp.value && prev) { prev.value = ''; prev.focus(); e.preventDefault(); }
        else { inp.value = ''; }
      }
    });
    inp.addEventListener('focus', () => clearSelection());
    wrapper.appendChild(inp);
    rackDiv.appendChild(wrapper);
  }
}

// Retourne le contenu du chevalet sous forme de chaîne
function getRackString() {
  const rackDiv = document.getElementById('rackdiv');
  const inputs = rackDiv.querySelectorAll('input.rack-input');
  let s = '';
  inputs.forEach(inp => {
    const v = inp.value || '';
    s += v ? v.toUpperCase() : '';
  });
  return s;
}


// Calcule et affiche les meilleurs coups
async function computeMoves() {
  showLoader(true);
  try {
    const rack = getRackString();
    let topk = 10;
    try {
      const topkEl = document.getElementById('topk');
      if (topkEl) {
        const val = parseInt(topkEl.value, 10);
        if (!Number.isNaN(val) && val > 0) topk = val;
      }
    } catch (e) { }
    // Appel GET à /api/moves avec rack et topk en query string
    const params = new URLSearchParams({ rack, topk });
    const res = await api(`/api/moves?${params.toString()}`);
    renderMovesList(res.moves);
  } finally {
    showLoader(false);
  }
}

// Affiche la liste des coups possibles
async function renderMoves() {
  showLoader(true);
  try {
    const moves = (await api(`/api/moves?topk=${document.getElementById('topk').value || 10}`)).moves || [];
    renderMovesList(moves);
  } finally {
    showLoader(false);
  }
}
function showLoader(show) {
  const loader = document.getElementById('loader');
  if (!loader) return;
  loader.classList.toggle('d-none', !show);
}

// Affiche la liste des coups dans l'interface
function renderMovesList(moves) {
  const movesList = document.getElementById('moves');
  movesList.innerHTML = '';
  if (!moves || moves.length === 0) {
    showNoMovesMessage(movesList);
    return;
  }
  moves.forEach(move => {
    const li = document.createElement('li');
    li.className = 'list-group-item move-item';
    li.innerHTML = `<div class="move-main"><strong>${move.score ?? ''}</strong> ${move.word ?? move.text ?? ''} @ ${move.row !== undefined ? move.row + 1 : ''},${move.col !== undefined ? move.col + 1 : ''} ${move.direction ?? ''}</div>`;
    const defBtn = document.createElement('a');
    defBtn.className = 'btn btn-sm btn-outline-info ms-2';
    defBtn.textContent = 'Chercher définition';
    const wordForUrl = encodeURIComponent(String(move.word || move.text || '').toLowerCase());
    defBtn.href = `https://1mot.net/${wordForUrl}`;
    defBtn.target = '_blank';
    defBtn.rel = 'noopener noreferrer';
    defBtn.addEventListener('click', e => e.stopPropagation());
    li.appendChild(defBtn);
    li.addEventListener('mouseenter', () => highlightMove(move, move.idx));
    li.addEventListener('mouseleave', e => {
      const boardEl = document.getElementById('board');
      const rel = e.relatedTarget;
      if (rel && boardEl && boardEl.contains(rel)) return;
      clearPreview();
    });
    li.addEventListener('click', async () => { await applyMoveByIdx(move.idx); });
    li.style.cursor = 'pointer';
    li.title = 'Survoler pour prévisualiser, cliquer pour appliquer';
    movesList.appendChild(li);
  });
}

// Affiche un message indiquant qu'aucun coup n'a été trouvé
function showNoMovesMessage(parentEl) {
  const ul = parentEl || document.getElementById('moves');
  if (!ul) return;
  ul.innerHTML = '';
  const li = document.createElement('li');
  li.className = 'list-group-item text-muted';
  li.textContent = 'Aucun coup trouvé';
  li.style.cursor = 'default';
  li.title = 'Aucun coup disponible pour le chevalet courant';
  ul.appendChild(li);
}


// Efface la prévisualisation des coups sur le plateau
function clearPreview() {
  document.querySelectorAll('.cell.highlight').forEach(x => x.classList.remove('highlight'));
  document.querySelectorAll('.preview-tile').forEach(x => x.remove());
}

// Met en surbrillance un coup sur le plateau
function highlightMove(mv, mvIdx) {
  clearPreview();
  for (const p of mv.placements || []) {
    const r = p[0], c = p[1];
    const sel = document.querySelector(`.cell[data-r='${r}'][data-c='${c}']`);
    if (!sel) continue;
    sel.classList.add('highlight');
    const hasPlaced = !!sel.querySelector('.placed-tile');
    if (!hasPlaced) {
      const [, , ch, is_blank] = p;
      const preview = document.createElement('div');
      preview.className = 'preview-tile' + (is_blank ? ' blank' : '');
      const letter = document.createElement('div'); letter.className = 'tile-letter'; letter.textContent = String(ch).toUpperCase();
      const score = document.createElement('div'); score.className = 'tile-score';
      const val = currentMeta?.values?.[String(ch).toUpperCase()] ?? '';
      score.textContent = is_blank ? '' : String(val);
      preview.append(letter, score);
      if (typeof mvIdx !== 'undefined') preview.dataset.mvIdx = String(mvIdx);
      preview.addEventListener('click', async e => { e.stopPropagation(); const id = preview.dataset.mvIdx || mvIdx; if (typeof id !== 'undefined') await applyMoveByIdx(Number(id)); });
      sel.appendChild(preview);
    } else {
      sel.classList.add('preview-exists');
    }
  }
}

// Applique un coup sélectionné par son index
async function applyMoveByIdx(idx) {
  const res = await api('/api/apply_move', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ idx }) });
  try { if (res.placements) removeTilesFromRack(res.placements); } catch (e) { }
  await renderBoard();
  committedLines = (await api('/api/board')).lines;
  // Après application d'un coup, vider la liste des meilleurs coups sans afficher de message
  clearMovesList();
  clearPreview(); // Toujours effacer la prévisualisation après tout
}

// Vide la liste des meilleurs coups sans afficher de message
function clearMovesList() {
  const movesList = document.getElementById('moves');
  if (movesList) movesList.innerHTML = '';
}

// Retire les tuiles utilisées du chevalet
function removeTilesFromRack(placements) {
  const rackDiv = document.getElementById('rackdiv');
  if (!rackDiv) return;
  const inputs = Array.from(rackDiv.querySelectorAll('input.rack-input'));
  const vals = inputs.map(i => i.value || '');
  for (const p of placements) {
    const ch = String(p[2] || '').toUpperCase();
    const is_blank = !!p[3];
    let found = -1;
    if (is_blank) {
      found = vals.findIndex(v => v === '?');
    } else {
      found = vals.findIndex(v => v && v.toUpperCase() === ch && v === v.toUpperCase());
      if (found === -1) {
        found = vals.findIndex(v => v && v.toUpperCase() === ch);
      }
    }
    if (found !== -1) {
      vals[found] = '';
    }
  }
  const compact = vals.filter(v => v && v.length > 0);
  while (compact.length < inputs.length) compact.push('');
  inputs.forEach((inp, i) => { inp.value = compact[i] || ''; });
}