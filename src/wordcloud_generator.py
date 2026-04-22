"""
Generate word-cloud PNG cards from association frequency maps.

One PNG per answer, one per category.
Also produces a flashcards.html index for easy browsing.
"""
import json
import logging
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")   # non-interactive backend – safe for headless runs
import matplotlib.pyplot as plt
from tqdm import tqdm
from wordcloud import WordCloud

from . import config as cfg
from .associations import load_json, run as build_associations

log = logging.getLogger(__name__)

# ── Helpers ────────────────────────────────────────────────────────────────

_RE_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

def _safe_filename(name: str) -> str:
    """Convert an arbitrary string to a filesystem-safe filename (no extension)."""
    name = _RE_UNSAFE.sub("_", name.strip())
    name = re.sub(r"\s+", "_", name)
    return name[:120]   # cap length


def _make_wordcloud(freq: dict[str, int]) -> WordCloud:
    return WordCloud(
        width           = cfg.WC_WIDTH,
        height          = cfg.WC_HEIGHT,
        background_color= cfg.WC_BG_COLOR,
        max_words       = cfg.WC_MAX_WORDS,
        colormap        = cfg.WC_COLORMAP,
        prefer_horizontal=0.9,
    ).generate_from_frequencies(freq)


def _save_card(wc: WordCloud, title: str, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(cfg.WC_WIDTH / 100, cfg.WC_HEIGHT / 100))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    ax.set_title(title, fontsize=13, pad=8, wrap=True)
    fig.tight_layout(pad=0.5)
    fig.savefig(out_path, dpi=cfg.WC_DPI, bbox_inches="tight")
    plt.close(fig)


# ── Public API ─────────────────────────────────────────────────────────────

def generate_cards(force: bool = False) -> None:
    """
    Generate all answer and category PNG word-cloud cards.

    Parameters
    ----------
    force : bool
        Regenerate cards even if they already exist on disk.
    """
    cfg.OUTPUT_ANSWERS_DIR.mkdir(parents=True, exist_ok=True)
    cfg.OUTPUT_CATS_DIR.mkdir(parents=True, exist_ok=True)

    answer_map, cat_map = build_associations(force=False)

    _generate_batch(answer_map, cfg.OUTPUT_ANSWERS_DIR, label="answer", force=force)
    _generate_batch(cat_map,    cfg.OUTPUT_CATS_DIR,    label="category", force=force)

    _write_html_index(answer_map, cat_map)


def _generate_batch(
    assoc_map: dict[str, dict[str, int]],
    out_dir: Path,
    label: str,
    force: bool,
) -> None:
    skipped = 0
    for name, freq in tqdm(assoc_map.items(), desc=f"Generating {label} cards"):
        if not freq:
            continue
        out_path = out_dir / f"{_safe_filename(name)}.png"
        if out_path.exists() and not force:
            skipped += 1
            continue
        try:
            wc = _make_wordcloud(freq)
            _save_card(wc, title=name, out_path=out_path)
        except Exception as exc:   # noqa: BLE001
            log.warning("Failed to generate card for '%s': %s", name, exc)

    log.info(
        "  %s cards: %d generated, %d skipped (already exist).",
        label.capitalize(),
        len(assoc_map) - skipped,
        skipped,
    )



_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Jeopardy! Word-Cloud Flashcards</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Segoe UI',sans-serif;background:#0d0d0d;color:#eee;min-height:100vh}
    header{background:#1a1a1a;border-bottom:3px solid #f5c518;padding:1rem 2rem}
    header h1{color:#f5c518;font-size:1.8rem;text-align:center;margin-bottom:.25rem}
    header p{color:#888;text-align:center;font-size:.85rem}
    header a{color:#f5c518}
    /* Tabs */
    .tabs{display:flex;justify-content:center;margin:1.5rem auto 0;max-width:600px;border:1px solid #333;border-radius:8px;overflow:hidden}
    .tab-btn{flex:1;padding:.65rem 1rem;background:#1a1a1a;border:none;color:#aaa;font-size:.95rem;cursor:pointer;transition:all .2s}
    .tab-btn.active{background:#f5c518;color:#000;font-weight:700}
    .tab-btn:hover:not(.active){background:#2a2a2a;color:#eee}
    /* Banner */
    .banner{display:none;background:#1a2e1a;border:1px solid #2e5e2e;border-radius:6px;padding:.65rem 1.2rem;margin:.9rem auto 0;max-width:780px;color:#7dbd7d;font-size:.9rem;align-items:center;gap:.75rem;flex-wrap:wrap}
    .banner strong{color:#a8e8a8}
    .banner .back-btn{background:#2a4a2a;border:1px solid #3a7a3a;color:#8ccc8c;padding:.25rem .7rem;border-radius:4px;cursor:pointer;font-size:.82rem;margin-left:auto;white-space:nowrap}
    .banner .back-btn:hover{background:#f5c518;color:#000;border-color:#f5c518}
    /* Controls */
    .controls{max-width:780px;margin:1.25rem auto;padding:0 1rem;display:flex;gap:.75rem;align-items:center}
    .search-wrap{position:relative;flex:1}
    .search-wrap input{width:100%;padding:.6rem 1rem .6rem 2.4rem;font-size:1rem;border-radius:6px;border:1px solid #333;background:#1e1e1e;color:#eee;outline:none}
    .search-wrap input:focus{border-color:#f5c518}
    .search-icon{position:absolute;left:.7rem;top:50%;transform:translateY(-50%);color:#555;pointer-events:none}
    .count{color:#777;font-size:.85rem;white-space:nowrap}
    select{background:#1e1e1e;border:1px solid #333;color:#ccc;padding:.5rem .7rem;border-radius:6px;font-size:.9rem;cursor:pointer}
    select:focus{outline:none;border-color:#f5c518}
    /* Domain grid */
    .dom-grid{display:flex;flex-wrap:wrap;gap:1.25rem;justify-content:center;padding:1.25rem 1rem 0;max-width:1200px;margin:0 auto}
    .dom-card{background:#1e1e1e;border-radius:10px;padding:1.4rem 1.2rem;width:210px;cursor:pointer;border:2px solid #2a2a2a;border-top:4px solid var(--dc,#f5c518);transition:border-color .2s,transform .15s;text-align:center}
    .dom-card:hover,.dom-card:focus{border-color:var(--dc,#f5c518);transform:translateY(-3px);outline:none}
    .dom-name{font-size:.97rem;font-weight:700;color:#eee;margin-bottom:.5rem;line-height:1.25}
    .dom-count{font-size:1.4rem;font-weight:800;color:var(--dc,#f5c518);margin:.25rem 0}
    .dom-sub{font-size:.75rem;color:#555}
    /* Row list (categories / lists within domain) */
    .row-list{max-width:840px;margin:0 auto;padding:.5rem 1rem 2rem}
    .row{display:flex;align-items:center;gap:.75rem;padding:.7rem 1.1rem;margin:.3rem 0;background:#1e1e1e;border-radius:6px;cursor:pointer;border:1px solid #2a2a2a;transition:border-color .15s,background .15s}
    .row:hover,.row:focus{border-color:#f5c518;background:#252525;outline:none}
    .row-name{flex:1;font-size:.92rem;color:#ddd}
    .row-badge{font-size:.75rem;padding:.18rem .6rem;border-radius:10px;white-space:nowrap;background:#1a3a1a;color:#7dbd7d}
    .row-arrow{color:#444;font-size:.8rem}
    .row:hover .row-arrow,.row:focus .row-arrow{color:#f5c518}
    /* Answer card grid */
    .grid{display:flex;flex-wrap:wrap;gap:1rem;justify-content:center;padding:1rem 1rem 0;max-width:1400px;margin:0 auto;min-height:250px}
    .card{background:#1e1e1e;border-radius:8px;padding:.5rem;width:300px;cursor:pointer;border:2px solid transparent;transition:border-color .2s,transform .15s;box-shadow:0 2px 8px rgba(0,0,0,.5)}
    .card:hover{border-color:#f5c518;transform:translateY(-2px)}
    .card:focus{outline:2px solid #f5c518;outline-offset:2px}
    .label{text-align:center;font-size:.82rem;color:#bbb;padding:.3rem 0 .1rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .card img{width:100%;border-radius:4px;display:block}
    /* Shared */
    .empty{width:100%;text-align:center;color:#555;padding:4rem 0;font-size:1.1rem}
    .pagination{display:flex;justify-content:center;align-items:center;gap:.4rem;padding:1.5rem 1rem;flex-wrap:wrap}
    .pagination button{background:#1e1e1e;border:1px solid #333;color:#ccc;padding:.4rem .8rem;border-radius:5px;cursor:pointer;font-size:.9rem;transition:all .15s;min-width:36px}
    .pagination button:hover:not(:disabled){background:#2a2a2a;border-color:#f5c518;color:#f5c518}
    .pagination button.cur{background:#f5c518;border-color:#f5c518;color:#000;font-weight:700}
    .pagination button:disabled{opacity:.3;cursor:default}
    .pg-info{color:#666;font-size:.82rem}
    /* Lightbox */
    .lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.92);z-index:999;align-items:center;justify-content:center}
    .lb.open{display:flex}
    .lb-inner{background:#1a1a1a;border-radius:12px;padding:1.5rem;max-width:96vw;position:relative;display:flex;flex-direction:column;align-items:center;gap:1rem}
    .lb-title{color:#f5c518;font-size:1.3rem;font-weight:700;text-align:center;max-width:860px}
    .lb-img{max-width:min(900px,88vw);max-height:66vh;border-radius:6px;display:block}
    .lb-nav{display:flex;gap:1rem;align-items:center}
    .lb-btn{background:#2a2a2a;border:1px solid #444;color:#eee;padding:.5rem 1.3rem;border-radius:6px;cursor:pointer;font-size:1rem;transition:all .15s}
    .lb-btn:hover{background:#f5c518;color:#000;border-color:#f5c518}
    .lb-close{position:absolute;top:.6rem;right:.8rem;background:none;border:none;color:#777;font-size:1.6rem;cursor:pointer;line-height:1}
    .lb-close:hover{color:#f5c518}
    .lb-counter{color:#666;font-size:.85rem}
    /* ── Flashcards tab ───────────────────────────────── */
    /* Tree: domain > list > answer */
    .fc-tree{max-width:900px;margin:0 auto;padding:.5rem 1rem 3rem}
    .fc-domain{margin:.5rem 0;border:1px solid #2a2a2a;border-radius:8px;overflow:hidden}
    .fc-dom-hdr{display:flex;align-items:center;gap:.75rem;padding:.75rem 1.1rem;background:#1a1a1a;cursor:pointer;border:none;width:100%;text-align:left;color:#eee}
    .fc-dom-hdr:hover{background:#222}
    .fc-dom-hdr .arrow{font-size:.7rem;color:#555;transition:transform .2s;flex-shrink:0}
    .fc-dom-hdr.open .arrow{transform:rotate(90deg);color:#f5c518}
    .fc-dom-name{flex:1;font-weight:700;font-size:.95rem}
    .fc-dom-badge{font-size:.73rem;color:#555;white-space:nowrap}
    .fc-dom-body{display:none;background:#111}
    .fc-dom-body.open{display:block}
    .fc-list{border-top:1px solid #1e1e1e}
    .fc-list-hdr{display:flex;align-items:center;gap:.65rem;padding:.6rem 1.1rem .6rem 2rem;cursor:pointer;border:none;width:100%;text-align:left;background:transparent;color:#ccc}
    .fc-list-hdr:hover{background:#1a1a1a;color:#eee}
    .fc-list-hdr .arrow{font-size:.65rem;color:#444;transition:transform .2s}
    .fc-list-hdr.open .arrow{transform:rotate(90deg);color:#f5c518}
    .fc-list-name{flex:1;font-size:.88rem}
    .fc-list-badge{font-size:.72rem;color:#555;white-space:nowrap}
    .fc-ans-grid{display:none;flex-wrap:wrap;gap:.35rem;padding:.4rem 2.2rem .7rem 3rem;background:#0f0f0f}
    .fc-ans-grid.open{display:flex}
    .fc-ans-chip{font-size:.78rem;background:#1a1a1a;border:1px solid #2a2a2a;color:#bbb;padding:.28rem .65rem;border-radius:12px;cursor:pointer;transition:border-color .15s,color .15s}
    .fc-ans-chip:hover{border-color:#f5c518;color:#f5c518}
    /* Flashcard modal */
    .fc-modal{display:none;position:fixed;inset:0;background:rgba(0,0,0,.93);z-index:1000;align-items:center;justify-content:center;padding:1rem}
    .fc-modal.open{display:flex}
    .fc-card{background:#111;border:2px solid #f5c518;border-radius:14px;width:min(820px,96vw);max-height:90vh;overflow-y:auto;position:relative;padding:0}
    .fc-card-top{background:#1a1a00;border-bottom:2px solid #f5c518;padding:1.1rem 1.5rem .9rem}
    .fc-card-answer{color:#f5c518;font-size:1.6rem;font-weight:800;margin-bottom:.25rem;line-height:1.2}
    .fc-card-meta{color:#666;font-size:.78rem}
    .fc-card-body{padding:1rem 1.5rem 1.4rem}
    .fc-section-title{font-size:.72rem;font-weight:700;color:#555;letter-spacing:.08em;text-transform:uppercase;margin:.9rem 0 .4rem;border-bottom:1px solid #222;padding-bottom:.2rem}
    .fc-clue-block{margin:.35rem 0;display:flex;gap:.6rem;align-items:flex-start}
    .fc-clue-cat{font-size:.7rem;color:#666;white-space:nowrap;padding-top:.15rem;min-width:80px;max-width:120px;overflow:hidden;text-overflow:ellipsis;flex-shrink:0}
    .fc-clue-text{font-size:.88rem;color:#ccc;line-height:1.45}
    .fc-close{position:absolute;top:.65rem;right:.8rem;background:none;border:none;color:#777;font-size:1.6rem;cursor:pointer;line-height:1}
    .fc-close:hover{color:#f5c518}
    .fc-nav{display:flex;gap:.75rem;justify-content:center;padding:.75rem 1.5rem;border-top:1px solid #222;background:#0d0d0d}
    .fc-nav-btn{background:#1e1e1e;border:1px solid #333;color:#ccc;padding:.45rem 1.1rem;border-radius:6px;cursor:pointer;font-size:.9rem}
    .fc-nav-btn:hover:not(:disabled){background:#f5c518;color:#000;border-color:#f5c518}
    .fc-nav-btn:disabled{opacity:.3;cursor:default}
    .fc-nav-ctr{color:#666;font-size:.82rem;align-self:center}
    /* Flashcard tab controls */
    .fc-controls{max-width:900px;margin:.9rem auto .3rem;padding:0 1rem;display:flex;gap:.75rem;align-items:center}
    .fc-controls input{flex:1;padding:.55rem 1rem;font-size:.95rem;border-radius:6px;border:1px solid #333;background:#1e1e1e;color:#eee;outline:none}
    .fc-controls input:focus{border-color:#f5c518}
    .fc-expand-btn{background:#1e1e1e;border:1px solid #333;color:#aaa;padding:.5rem .85rem;border-radius:6px;cursor:pointer;font-size:.82rem;white-space:nowrap}
    .fc-expand-btn:hover{border-color:#f5c518;color:#f5c518}
  </style>
</head>
<body>
<header>
  <h1>Jeopardy! Word-Cloud Flashcards</h1>
  <p>Inspired by <a href="https://colindavy.medium.com/how-i-won-jeopardy-with-data-science-c2e9b52a1958" target="_blank">Colin Davy's method</a>. Largest words = strongest clue triggers.</p>
</header>

<div style="text-align:center;margin-top:1.5rem">
  <div class="tabs">
    <button class="tab-btn active" id="tab-answers"    onclick="switchTab('answers')">Answers <span id="badge-answers"    style="opacity:.7"></span></button>
    <button class="tab-btn"        id="tab-categories" onclick="switchTab('categories')">Categories <span id="badge-categories" style="opacity:.7"></span></button>
    <button class="tab-btn"        id="tab-analysis"   onclick="switchTab('analysis')">Study Lists <span id="badge-analysis"   style="opacity:.7"></span></button>
    <button class="tab-btn"        id="tab-flashcards" onclick="switchTab('flashcards')">Flashcards <span id="badge-flashcards" style="opacity:.7"></span></button>
  </div>
</div>

<div class="banner" id="banner"></div>

<div class="controls" id="controls">
  <div class="search-wrap">
    <span class="search-icon">&#128269;</span>
    <input type="text" id="q" placeholder="Search answers..." oninput="onSearch()" autocomplete="off">
  </div>
  <select id="sort-sel" onchange="onSearch()">
    <option value="az">A to Z</option>
    <option value="za">Z to A</option>
  </select>
  <span class="count" id="count-lbl"></span>
</div>

<div id="main-area"></div>
<div class="pagination" id="pager"></div>

<!-- Flashcard modal -->
<div class="fc-modal" id="fc-modal" role="dialog" aria-modal="true">
  <div class="fc-card">
    <button class="fc-close" onclick="fcClose()" title="Close (Esc)">&#x2715;</button>
    <div class="fc-card-top">
      <div class="fc-card-answer" id="fc-answer"></div>
      <div class="fc-card-meta" id="fc-meta"></div>
    </div>
    <div class="fc-card-body" id="fc-body"></div>
    <div class="fc-nav">
      <button class="fc-nav-btn" id="fc-prev" onclick="fcMove(-1)">&#8592; Prev</button>
      <span class="fc-nav-ctr" id="fc-ctr"></span>
      <button class="fc-nav-btn" id="fc-next" onclick="fcMove(1)">Next &#8594;</button>
    </div>
  </div>
</div>

<div class="lb" id="lb" role="dialog" aria-modal="true">
  <div class="lb-inner">
    <button class="lb-close" onclick="lbClose()" title="Close (Esc)">&#x2715;</button>
    <div class="lb-title" id="lb-title"></div>
    <img class="lb-img" id="lb-img" src="" alt="">
    <div class="lb-nav">
      <button class="lb-btn" onclick="lbMove(-1)">&#8592; Prev</button>
      <span class="lb-counter" id="lb-ctr"></span>
      <button class="lb-btn" onclick="lbMove(1)">Next &#8594;</button>
    </div>
  </div>
</div>

<script>
var PER_PAGE_CARDS = 48;
var PER_PAGE_LIST  = 100;

var ANSWERS        = __ANSWERS_JSON__;
var CATEGORIES     = __CATS_JSON__;
var CAT_ANSWERS    = __CAT_ANSWERS_JSON__;
var ANALYSIS_LISTS = __ANALYSIS_LISTS_JSON__;
var DOMAINS        = __DOMAINS_JSON__;

/* Flashcard data — lazily fetched on first open */
var FC_DATA  = null;   /* { answer: {clues:[{cat,text}], categories:[], total_clues:n} } */
var FC_QUEUE = [];     /* callbacks waiting for FC_DATA */
function loadFcData(cb) {
  if (FC_DATA) { cb(FC_DATA); return; }
  FC_QUEUE.push(cb);
  if (FC_QUEUE.length > 1) return;
  fetch('data/processed/flashcards.json')
    .then(function(r){ return r.json(); })
    .then(function(d){
      FC_DATA = d;
      FC_QUEUE.forEach(function(fn){ fn(d); });
      FC_QUEUE = [];
    })
    .catch(function(e){ console.error('flashcards.json load error', e); });
}

/* Domain color palette */
var DOM_COLORS = ['#2a8a50','#1a5aaa','#aa2a2a','#6a2aaa','#1a7a6a','#aa5a1a','#1a7aaa','#2a6a50','#1a1a8a','#7a6a1a'];

/* Precompute list answer counts and domain answer counts */
var LIST_COUNTS = {};
(function(){ for (var k in ANALYSIS_LISTS) LIST_COUNTS[k] = ANALYSIS_LISTS[k].length; })();

var DOM_COUNTS = {};
var DOM_LIST = Object.keys(DOMAINS);
DOM_LIST.forEach(function(d, i) {
  var s = new Set();
  DOMAINS[d].forEach(function(l){ (ANALYSIS_LISTS[l]||[]).forEach(function(a){ s.add(a); }); });
  DOM_COUNTS[d] = s.size;
});

/* Build ANSWER set for quick lookup */
var ANSWER_SET = new Set(ANSWERS.map(function(a){ return a.n; }));

/* Category list sorted by answer count desc */
var CAT_LIST = CATEGORIES.map(function(c){
  return {n: c.n, count: (CAT_ANSWERS[c.n]||[]).length};
}).sort(function(a,b){ return b.count - a.count || a.n.localeCompare(b.n); });

/* ── State ──────────────────────────────────────────────────────────────── */
var tab       = 'answers';
var filtered  = [];
var page      = 0;
var lbIdx     = 0;
var catFilter = null;   /* answers tab: active category filter */
var anaDomain = null;   /* analysis tab: selected domain (null = top level) */
var anaList   = null;   /* analysis tab: selected list (null = domain list view) */
/* Flashcards tab */
var fcList    = [];     /* ordered list of answer names in current fc view */
var fcIdx     = 0;     /* index into fcList currently shown in modal */
var FC_Q      = '';    /* current search query on fc tab */
var FC_OPEN_DOMAINS = {};  /* domain name -> bool expanded */
var FC_OPEN_LISTS   = {};  /* list name   -> bool expanded */

/* ── Init ───────────────────────────────────────────────────────────────── */
function init() {
  document.getElementById('badge-answers').textContent    = '(' + ANSWERS.length + ')';
  document.getElementById('badge-categories').textContent = '(' + CATEGORIES.length + ')';
  document.getElementById('badge-analysis').textContent   = '(' + DOM_LIST.length + ' domains)';
  document.getElementById('badge-flashcards').textContent = '(' + ANSWERS.length + ')';
  document.getElementById('main-area').addEventListener('click', delegateClick);
  document.getElementById('main-area').addEventListener('keydown', function(e){
    if (e.key === 'Enter') delegateClick(e);
  });
  applyFilter();
}

function delegateClick(e) {
  /* Categories tab: open category filter */
  var catRow = e.target.closest('[data-cat]');
  if (catRow) { openCategory(catRow.dataset.cat); return; }
  /* Analysis tab: domain card */
  var domCard = e.target.closest('[data-domain]');
  if (domCard) { openDomain(domCard.dataset.domain); return; }
  /* Analysis tab: list row */
  var listRow = e.target.closest('[data-list]');
  if (listRow) { openList(listRow.dataset.list); return; }
  /* Flashcards tab: toggle domain */
  var fcDom = e.target.closest('[data-fc-domain]');
  if (fcDom) { toggleFcDomain(fcDom.dataset.fcDomain); return; }
  /* Flashcards tab: toggle list */
  var fcLst = e.target.closest('[data-fc-list]');
  if (fcLst) { toggleFcList(fcLst.dataset.fcList); return; }
  /* Flashcards tab: open a flashcard */
  var fcAns = e.target.closest('[data-fc-ans]');
  if (fcAns) { openFcModal(fcAns.dataset.fcAns, fcAns.dataset.fcList); return; }
}

/* ── Tab switching ──────────────────────────────────────────────────────── */
function switchTab(t) {
  catFilter = null;
  tab = t;
  if (t === 'analysis') { anaDomain = null; anaList = null; }
  document.querySelectorAll('.tab-btn').forEach(function(b){ b.classList.remove('active'); });
  document.getElementById('tab-' + t).classList.add('active');
  document.getElementById('q').value = '';
  page = 0;
  /* hide flashcard-specific search when leaving that tab */
  var fcCtrl = document.getElementById('fc-ctrl');
  if (fcCtrl) fcCtrl.style.display = (t === 'flashcards') ? '' : 'none';
  syncControls();
  updateBanner();
  if (t === 'flashcards') { renderFcTab(); return; }
  applyFilter();
}

function syncControls() {
  var ctrl = document.getElementById('controls');
  if (tab === 'flashcards') { ctrl.style.display = 'none'; return; }
  ctrl.style.display = '';
  var isCards = (tab === 'answers') || (tab === 'analysis' && anaList !== null);
  var sortSel = document.getElementById('sort-sel');
  if (isCards) {
    sortSel.innerHTML = '<option value="az">A to Z</option><option value="za">Z to A</option>';
    document.getElementById('q').placeholder = 'Search answers...';
  } else if (tab === 'categories') {
    sortSel.innerHTML = '<option value="count">Most answers first</option><option value="az">A to Z</option>';
    document.getElementById('q').placeholder = 'Search categories...';
  } else {
    /* analysis domain/list views */
    sortSel.innerHTML = '<option value="az">A to Z</option>';
    document.getElementById('q').placeholder = tab === 'analysis' && anaDomain ? 'Search lists...' : 'Search domains...';
  }
}

function onSearch() { page = 0; applyFilter(); }

/* ── Filter & render dispatch ────────────────────────────────────────────── */
function applyFilter() {
  var q    = document.getElementById('q').value.toLowerCase().trim();
  var sort = document.getElementById('sort-sel').value;

  if (tab === 'analysis') {
    if (anaList !== null) {
      /* card grid for a specific study list */
      var pool = (ANALYSIS_LISTS[anaList] || [])
        .filter(function(n){ return ANSWER_SET.has(n); })
        .map(function(n){ return ANSWERS.find(function(a){ return a.n === n; }); })
        .filter(Boolean);
      pool = q ? pool.filter(function(d){ return d.n.toLowerCase().indexOf(q) !== -1; }) : pool;
      if (sort === 'za') pool = pool.slice().reverse();
      filtered = pool;
      renderCards();
    } else if (anaDomain !== null) {
      renderLists(q);
    } else {
      renderDomains(q);
    }
    return;
  }

  if (tab === 'categories') {
    var base = q ? CAT_LIST.filter(function(c){ return c.n.toLowerCase().indexOf(q) !== -1; }) : CAT_LIST.slice();
    if (sort === 'az') base = base.slice().sort(function(a,b){ return a.n.localeCompare(b.n); });
    filtered = base;
    renderRowList(filtered, 'cat');
    return;
  }

  /* answers tab */
  var pool2 = catFilter
    ? ANSWERS.filter(function(d){ return (CAT_ANSWERS[catFilter]||[]).indexOf(d.n) !== -1; })
    : ANSWERS.slice();
  var list2 = q ? pool2.filter(function(d){ return d.n.toLowerCase().indexOf(q) !== -1; }) : pool2;
  if (sort === 'za') list2 = list2.slice().reverse();
  filtered = list2;
  renderCards();
}

/* ── Analysis renders ────────────────────────────────────────────────────── */
function renderDomains(q) {
  document.getElementById('pager').innerHTML = '';
  var doms = q ? DOM_LIST.filter(function(d){ return d.toLowerCase().indexOf(q) !== -1; }) : DOM_LIST;
  document.getElementById('count-lbl').textContent = doms.length + ' domains';

  if (!doms.length) {
    document.getElementById('main-area').innerHTML = '<p class="empty">No domains match.</p>';
    return;
  }
  var html = '<div class="dom-grid">';
  doms.forEach(function(d) {
    var idx = DOM_LIST.indexOf(d);
    var color = DOM_COLORS[idx % DOM_COLORS.length];
    var nLists = (DOMAINS[d] || []).length;
    html += '<div class="dom-card" tabindex="0" data-domain="' + esc(d) + '" style="--dc:' + color + '">'
          + '<div class="dom-name">' + esc(d) + '</div>'
          + '<div class="dom-count">' + DOM_COUNTS[d] + '</div>'
          + '<div class="dom-sub">answers across ' + nLists + ' list' + (nLists === 1 ? '' : 's') + '</div>'
          + '</div>';
  });
  html += '</div>';
  document.getElementById('main-area').innerHTML = html;
}

function renderLists(q) {
  document.getElementById('pager').innerHTML = '';
  var lists = (DOMAINS[anaDomain] || []).filter(function(l){ return l in ANALYSIS_LISTS; });
  if (q) lists = lists.filter(function(l){ return l.toLowerCase().indexOf(q) !== -1; });
  document.getElementById('count-lbl').textContent = lists.length + ' lists';

  if (!lists.length) {
    document.getElementById('main-area').innerHTML = '<p class="empty">No lists match.</p>';
    return;
  }
  var html = '<div class="row-list">';
  lists.forEach(function(l) {
    html += '<div class="row" tabindex="0" data-list="' + esc(l) + '">'
          + '<span class="row-name">' + esc(l) + '</span>'
          + '<span class="row-badge">' + (LIST_COUNTS[l] || 0) + ' answers</span>'
          + '<span class="row-arrow">&#9658;</span></div>';
  });
  html += '</div>';
  document.getElementById('main-area').innerHTML = html;
}

/* ── Card grid render ────────────────────────────────────────────────────── */
function renderCards() {
  var total   = filtered.length;
  var perPage = PER_PAGE_CARDS;
  var pages   = Math.ceil(total / perPage) || 1;
  if (page >= pages) page = Math.max(0, pages - 1);
  var start = page * perPage;
  var slice = filtered.slice(start, start + perPage);

  document.getElementById('count-lbl').textContent = total
    ? (start + 1) + '-' + (start + slice.length) + ' of ' + total
    : '0 results';

  if (!slice.length) {
    document.getElementById('main-area').innerHTML = '<p class="empty">No results match your search.</p>';
    document.getElementById('pager').innerHTML = '';
    return;
  }
  var html = '<div class="grid">';
  slice.forEach(function(d, i) {
    var idx = start + i, safe = esc(d.n);
    html += '<div class="card" tabindex="0" onclick="lbOpen(' + idx + ')" onkeydown="if(event.key==&quot;Enter&quot;)lbOpen(' + idx + ')">'
          + '<p class="label" title="' + safe + '">' + safe + '</p>'
          + '<img src="' + d.s + '" alt="' + safe + '" loading="lazy"></div>';
  });
  html += '</div>';
  document.getElementById('main-area').innerHTML = html;
  renderPager(pages);
  window.scrollTo({top: 0, behavior: 'smooth'});
}

/* ── Category row list render ────────────────────────────────────────────── */
function renderRowList(items, type) {
  var total   = items.length;
  var perPage = PER_PAGE_LIST;
  var pages   = Math.ceil(total / perPage) || 1;
  if (page >= pages) page = Math.max(0, pages - 1);
  var start = page * perPage;
  var slice = items.slice(start, start + perPage);

  document.getElementById('count-lbl').textContent = total
    ? (start + 1) + '-' + (start + slice.length) + ' of ' + total
    : '0 results';

  if (!slice.length) {
    document.getElementById('main-area').innerHTML = '<p class="empty">No results match your search.</p>';
    document.getElementById('pager').innerHTML = '';
    return;
  }
  var html = '<div class="row-list">';
  slice.forEach(function(c) {
    var safe = esc(c.n);
    var attr = 'data-cat="' + safe + '"';
    html += '<div class="row" tabindex="0" ' + attr + '>'
          + '<span class="row-name">' + safe + '</span>'
          + '<span class="row-badge">' + c.count + (c.count === 1 ? ' answer' : ' answers') + '</span>'
          + '<span class="row-arrow">&#9658;</span></div>';
  });
  html += '</div>';
  document.getElementById('main-area').innerHTML = html;
  renderPager(pages);
  window.scrollTo({top: 0, behavior: 'smooth'});
}

/* ── Categories tab navigation ───────────────────────────────────────────── */
function openCategory(name) {
  catFilter = name;
  tab = 'answers';
  document.querySelectorAll('.tab-btn').forEach(function(b){ b.classList.remove('active'); });
  document.getElementById('tab-answers').classList.add('active');
  document.getElementById('sort-sel').innerHTML = '<option value="az">A to Z</option><option value="za">Z to A</option>';
  document.getElementById('q').placeholder = 'Search answers...';
  document.getElementById('q').value = '';
  page = 0;
  updateBanner();
  applyFilter();
}

function clearCatFilter() {
  catFilter = null;
  tab = 'categories';
  document.querySelectorAll('.tab-btn').forEach(function(b){ b.classList.remove('active'); });
  document.getElementById('tab-categories').classList.add('active');
  document.getElementById('sort-sel').innerHTML = '<option value="count">Most answers first</option><option value="az">A to Z</option>';
  document.getElementById('q').placeholder = 'Search categories...';
  document.getElementById('q').value = '';
  page = 0;
  updateBanner();
  applyFilter();
}

/* ── Analysis tab navigation ─────────────────────────────────────────────── */
function openDomain(name) {
  anaDomain = name; anaList = null;
  syncControls();
  document.getElementById('q').value = '';
  page = 0;
  updateBanner();
  applyFilter();
}

function openList(name) {
  anaList = name;
  syncControls();
  document.getElementById('q').value = '';
  document.getElementById('sort-sel').value = 'az';
  page = 0;
  updateBanner();
  applyFilter();
}

function backToDomains() {
  anaDomain = null; anaList = null;
  syncControls();
  document.getElementById('q').value = '';
  updateBanner();
  applyFilter();
}

function backToLists() {
  anaList = null;
  syncControls();
  document.getElementById('q').value = '';
  updateBanner();
  applyFilter();
}

/* ── Banner ─────────────────────────────────────────────────────────────── */
function updateBanner() {
  var el = document.getElementById('banner');

  if (tab === 'answers' && catFilter) {
    var cnt = (CAT_ANSWERS[catFilter] || []).length;
    el.innerHTML = 'Category: <strong>' + esc(catFilter) + '</strong> &mdash; ' + cnt + ' answer cards'
      + '<button class="back-btn" onclick="clearCatFilter()">&#8592; All categories</button>';
    el.style.display = 'flex';
  } else if (tab === 'analysis' && anaList !== null) {
    var lCnt = LIST_COUNTS[anaList] || 0;
    el.innerHTML = esc(anaDomain) + ' &rsaquo; <strong>' + esc(anaList) + '</strong> &mdash; ' + lCnt + ' answers'
      + '<button class="back-btn" onclick="backToLists()">&#8592; Back to lists</button>';
    el.style.display = 'flex';
  } else if (tab === 'analysis' && anaDomain !== null) {
    var nL = (DOMAINS[anaDomain] || []).length;
    el.innerHTML = 'Study Lists &rsaquo; <strong>' + esc(anaDomain) + '</strong> &mdash; ' + nL + ' lists'
      + '<button class="back-btn" onclick="backToDomains()">&#8592; All domains</button>';
    el.style.display = 'flex';
  } else {
    el.style.display = 'none';
  }
}

/* ── Pagination ─────────────────────────────────────────────────────────── */
function renderPager(pages) {
  var el = document.getElementById('pager');
  if (pages <= 1) { el.innerHTML = ''; return; }
  var nums = pageNums(page, pages);
  var h = '<button onclick="go(' + (page-1) + ')"' + (page===0?' disabled':'') + '>&lsaquo; Prev</button>';
  nums.forEach(function(n) {
    if (n === '...') h += '<span class="pg-info" style="padding:0 .25rem">&hellip;</span>';
    else h += '<button class="' + (n===page?'cur':'') + '" onclick="go(' + n + ')">' + (n+1) + '</button>';
  });
  h += '<button onclick="go(' + (page+1) + ')"' + (page===pages-1?' disabled':'') + '>Next &rsaquo;</button>';
  h += '<span class="pg-info">Page ' + (page+1) + ' / ' + pages + '</span>';
  el.innerHTML = h;
}

function pageNums(cur, tot) {
  if (tot <= 7) { var a=[]; for(var i=0;i<tot;i++) a.push(i); return a; }
  var r=[0];
  if (cur>2) r.push('...');
  for(var i=Math.max(1,cur-1);i<=Math.min(tot-2,cur+1);i++) r.push(i);
  if(cur<tot-3) r.push('...');
  r.push(tot-1);
  return r;
}

function go(p) {
  var isCards = (tab==='answers')||(tab==='analysis'&&anaList!==null);
  var perPage = isCards ? PER_PAGE_CARDS : PER_PAGE_LIST;
  var pages = Math.ceil(filtered.length / perPage) || 1;
  if (p<0||p>=pages) return;
  page = p; applyFilter();
}

/* ── Lightbox ───────────────────────────────────────────────────────────── */
function lbOpen(idx) { lbIdx=idx; lbShow(); document.getElementById('lb').classList.add('open'); }
function lbClose()   { document.getElementById('lb').classList.remove('open'); }
function lbMove(d)   { lbIdx=(lbIdx+d+filtered.length)%filtered.length; lbShow(); }
function lbShow() {
  var d=filtered[lbIdx];
  document.getElementById('lb-title').textContent = d.n;
  var img=document.getElementById('lb-img'); img.src=d.s; img.alt=d.n;
  document.getElementById('lb-ctr').textContent = (lbIdx+1)+' / '+filtered.length;
}

document.getElementById('lb').addEventListener('click', function(e){ if(e.target===e.currentTarget) lbClose(); });
document.getElementById('fc-modal').addEventListener('click', function(e){ if(e.target===e.currentTarget) fcClose(); });
document.addEventListener('keydown', function(e) {
  if (document.getElementById('fc-modal').classList.contains('open')) {
    if (e.key==='Escape') fcClose();
    if (e.key==='ArrowRight'||e.key==='ArrowDown') fcMove(1);
    if (e.key==='ArrowLeft' ||e.key==='ArrowUp')   fcMove(-1);
    return;
  }
  if (!document.getElementById('lb').classList.contains('open')) return;
  if (e.key==='Escape') lbClose();
  if (e.key==='ArrowRight'||e.key==='ArrowDown') lbMove(1);
  if (e.key==='ArrowLeft' ||e.key==='ArrowUp')   lbMove(-1);
});

/* ── Flashcards tab ──────────────────────────────────────────────────────── */

function renderFcTab() {
  document.getElementById('pager').innerHTML = '';
  document.getElementById('banner').style.display = 'none';
  var area = document.getElementById('main-area');

  /* Build fc-specific controls */
  var ctrlExisting = document.getElementById('fc-ctrl');
  if (!ctrlExisting) {
    var ctrl = document.createElement('div');
    ctrl.id = 'fc-ctrl';
    ctrl.className = 'fc-controls';
    ctrl.innerHTML = '<input id="fc-q" type="text" placeholder="Search answers across all lists..." oninput="onFcSearch()" autocomplete="off">';
    area.parentNode.insertBefore(ctrl, area);
  }
  document.getElementById('fc-ctrl').style.display = '';

  renderFcTree();
}

function onFcSearch() {
  FC_Q = document.getElementById('fc-q') ? document.getElementById('fc-q').value.toLowerCase().trim() : '';
  renderFcTree();
}

function renderFcTree() {
  if (tab !== 'flashcards') return;
  var area = document.getElementById('main-area');
  var html = '<div class="fc-tree">';

  DOM_LIST.forEach(function(domName) {
    var lists = (DOMAINS[domName] || []).filter(function(l){ return l in ANALYSIS_LISTS; });
    /* filter lists/answers by search query */
    var visibleLists = lists.filter(function(l) {
      if (!FC_Q) return true;
      if (l.toLowerCase().indexOf(FC_Q) !== -1) return true;
      return (ANALYSIS_LISTS[l] || []).some(function(a){ return a.toLowerCase().indexOf(FC_Q) !== -1; });
    });
    if (!visibleLists.length) return;

    var domOpen = FC_OPEN_DOMAINS[domName] || FC_Q !== '';
    var sDom = esc(domName);
    var totalAns = (function(){
      var s = new Set();
      lists.forEach(function(l){ (ANALYSIS_LISTS[l]||[]).forEach(function(a){ s.add(a); }); });
      return s.size;
    })();

    html += '<div class="fc-domain">';
    html += '<button class="fc-dom-hdr' + (domOpen?' open':'') + '" data-fc-domain="' + sDom + '">';
    html += '<span class="arrow">&#9658;</span><span class="fc-dom-name">' + sDom + '</span>';
    html += '<span class="fc-dom-badge">' + visibleLists.length + ' lists &bull; ' + totalAns + ' answers</span></button>';
    html += '<div class="fc-dom-body' + (domOpen?' open':'') + '">';

    visibleLists.forEach(function(listName) {
      var answers = ANALYSIS_LISTS[listName] || [];
      var visAns = FC_Q
        ? answers.filter(function(a){ return a.toLowerCase().indexOf(FC_Q) !== -1; })
        : answers;
      if (!visAns.length) return;

      var listOpen = FC_OPEN_LISTS[listName] || FC_Q !== '';
      var sLst = esc(listName);
      html += '<div class="fc-list">';
      html += '<button class="fc-list-hdr' + (listOpen?' open':'') + '" data-fc-list="' + sLst + '">';
      html += '<span class="arrow">&#9658;</span><span class="fc-list-name">' + sLst + '</span>';
      html += '<span class="fc-list-badge">' + visAns.length + ' answers</span></button>';
      html += '<div class="fc-ans-grid' + (listOpen?' open':'') + '">';
      visAns.forEach(function(ans) {
        html += '<span class="fc-ans-chip" tabindex="0" data-fc-ans="' + esc(ans) + '" data-fc-list="' + sLst + '">' + esc(ans) + '</span>';
      });
      html += '</div></div>';
    });

    html += '</div></div>';
  });

  html += '</div>';
  area.innerHTML = html;
}

function toggleFcDomain(name) {
  FC_OPEN_DOMAINS[name] = !FC_OPEN_DOMAINS[name];
  renderFcTree();
}

function toggleFcList(name) {
  FC_OPEN_LISTS[name] = !FC_OPEN_LISTS[name];
  renderFcTree();
}

function openFcModal(ansName, listName) {
  /* Build the ordered answer list from the list this chip belongs to */
  var listAnswers = (ANALYSIS_LISTS[listName] || []).slice();
  fcList = listAnswers;
  fcIdx  = listAnswers.indexOf(ansName);
  if (fcIdx < 0) { fcList = [ansName]; fcIdx = 0; }
  loadFcData(function(){ fcRender(); });
  document.getElementById('fc-modal').classList.add('open');
}

function fcClose() {
  document.getElementById('fc-modal').classList.remove('open');
}

function fcMove(d) {
  fcIdx = (fcIdx + d + fcList.length) % fcList.length;
  fcRender();
}

function fcRender() {
  if (!FC_DATA) return;
  var ans  = fcList[fcIdx];
  var data = FC_DATA[ans];

  document.getElementById('fc-answer').textContent = ans;

  var meta = '';
  if (data) {
    meta = data.total_clues + ' Jeopardy clues';
    if (data.categories && data.categories.length) {
      meta += ' &bull; appeared in: ' + data.categories.slice(0,5).map(esc).join(', ');
      if (data.categories.length > 5) meta += ', ...';
    }
  }
  document.getElementById('fc-meta').innerHTML = meta;

  var body = '';
  if (!data) {
    body = '<p style="color:#555;padding:.5rem 0">No clue data available.</p>';
  } else {
    /* Group clues by category */
    var byCat = {};
    (data.clues || []).forEach(function(c) {
      if (!byCat[c.cat]) byCat[c.cat] = [];
      byCat[c.cat].push(c.text);
    });
    var cats = Object.keys(byCat);
    if (!cats.length) {
      body = '<p style="color:#555;padding:.5rem 0">No clue data available.</p>';
    } else {
      cats.forEach(function(cat) {
        body += '<div class="fc-section-title">' + esc(cat) + '</div>';
        byCat[cat].forEach(function(txt) {
          body += '<div class="fc-clue-block"><div class="fc-clue-text">' + esc(txt) + '</div></div>';
        });
      });
    }
  }
  document.getElementById('fc-body').innerHTML = body;

  /* Nav */
  document.getElementById('fc-ctr').textContent = (fcIdx+1) + ' / ' + fcList.length;
  document.getElementById('fc-prev').disabled = (fcList.length <= 1);
  document.getElementById('fc-next').disabled = (fcList.length <= 1);

  /* Scroll to top */
  document.querySelector('.fc-card').scrollTop = 0;
}

function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

init();
</script>
</body>
</html>
"""





def _build_list_analysis(df: "pd.DataFrame", answer_map: dict):
    """Return (lists_json, domains_json) for the Study Lists tab.

    Each "list" is a real Jeopardy category that is a high-quality study list
    (>= 5 matched top-1500 answers AND >= 25% of its clues test top-1500 answers).
    The top 400 eligible categories are taken and grouped into ~22 knowledge domains.
    """
    import re as _re, json as _json

    ans_set = set(answer_map.keys())

    # ── Find eligible categories ──────────────────────────────────────────
    df2 = df.copy()
    df2["_m"] = df2["answer"].isin(ans_set)
    stats = (
        df2.groupby("category")
        .agg(total=("answer", "count"), matched=("_m", "sum"))
        .reset_index()
    )
    stats["cov"] = stats["matched"] / stats["total"]
    eligible = (
        stats[(stats["matched"] >= 5) & (stats["cov"] >= 0.25)]
        .nlargest(400, "matched")
    )
    eligible_cats = set(eligible["category"].tolist())
    # Build a quick count lookup for sorting within domains
    match_count = dict(zip(eligible["category"], eligible["matched"]))

    # ── Build answer list per eligible category ───────────────────────────
    filt = df[df["answer"].isin(ans_set) & df["category"].isin(eligible_cats)]
    cat_answers = (
        filt.groupby("category")["answer"]
        .apply(lambda x: sorted(x.unique().tolist()))
        .to_dict()
    )
    analysis_lists = {c: v for c, v in cat_answers.items() if v}

    # ── Domain patterns ───────────────────────────────────────────────────
    # Each tuple: (domain_name, regex).  re.search() is used — ALL-CAPS names.
    DOMAIN_PATTERNS = [
        ("World Geography",
         r"WORLD GEOGRAPHY|^GEOGRAPHY$|COUNTRIES OF|WORLD CAPITAL|WORLD CIT|"
         r"AROUND THE WORLD|WORLD FACTS|WORLD TRAVEL|WORLD FLAGS|"
         r"^ISLANDS?$|^MOUNTAINS?$|BODIES OF WATER|^RIVERS?$|LAKES & RIVERS|^LAKES?$|"
         r"^SEAS?$|^OCEANS?$|^VOLCANOES?$|^PENINSULAS?$|^WATERFALLS?$|^CONTINENTS?$|"
         r"^EUROPE$|^ASIA$|^AFRICA$|^SOUTH AMERICA$|^AUSTRALIA$|^CANADA$|"
         r"WESTERN HEMISPHERE|^THE MIDDLE EAST$|"
         r"EUROPEAN GEOGRAPHY|EUROPEAN CAPITAL|EUROPEAN CIT|"
         r"^FORMER CAPITALS?$|^COUNTRIES$|^CAPITAL CIT|^NAME THAT COUNTRY$"),

        ("U.S. Geography",
         r"U\.S\. GEOGRAPH|U\.S\. CITIES|^U\.S\. STATES?$|^THE 50 STATES?$|^U\.S\.A\.$|"
         r"STATE CAPITAL|STATE NICKNAMES|STATE FACTS|STATE FLAGS|STATE MOTTOES|"
         r"STATE SONGS|STATE PARKS|STATE SEALS|STATE QUARTERS|STATE LICENSE|"
         r"STATE HOLIDAY|STATE OF THE UNION|STATES OF THE UNION|STATES BY COUNTIES|"
         r"COUNTIES BY STATE|^TRAVEL U\.S|AROUND THE USA|U\.S\. RIVERS|"
         r"^NEW ENGLAND$|U\.S\. LANDMARKS|STATE CAPITAL NICK|STATE CAPITAL ATTRACT|"
         r"^COUNTIES$|^NATIONAL PARKS$|^NATIONAL MONUMENTS$"),

        ("U.S. Presidents",
         r"^U\.S\. PRESIDENTS?$|^PRESIDENTS?$|^FIRST LADIES$|VICE.?PRESIDENTS?|"
         r"^HAIL TO THE CHIEF$|^PRESIDENTIAL|^BEFORE HE WAS PRESIDENT$|"
         r"PRESIDENTS? & FIRST LADIES|^PRESIDENTS? WIVES"),

        ("U.S. Government & Politics",
         r"^THE SUPREME COURT$|^GOVERNORS?$|^DEMOCRATS?$|^REPUBLICANS?$|"
         r"^THE WHITE HOUSE$|INAUGURAL ADDRESS|^POLITICS$|^POLITICIANS?$|"
         r"^THE U\.N\.$|^THE UNITED NATIONS$"),

        ("American History",
         r"AMERICAN HISTORY|U\.S\. HISTORY|^THE CIVIL WAR$|^CIVIL WAR$|"
         r"COLONIAL AMERICA|19th CENTURY AMERICA|THE AMERICAN REVOLUTION|"
         r"18th CENTURY AMERICA|^EARLY AMERICA$|^BLACK AMERICA$|"
         r"^THE 13 COLONIES$|^THE REVOLUTIONARY WAR$|^THE WAR OF 1812$|"
         r"^FAMOUS AMERICANS?$|^HISTORIC AMERICANS?$|^AMERICANA$|"
         r"^AMERICAN HODGEPODGE$"),

        ("World History & Eras",
         r"^WORLD HISTORY$|^HISTORY$|^ANCIENT HISTORY$|^EUROPEAN HISTORY$|"
         r"^THE MIDDLE AGES$|WORLD WAR II|WORLD WAR I\b|^WARS$|^MODERN HISTORY$|"
         r"^BRITISH HISTORY$|^RUSSIAN HISTORY$|^FRENCH HISTORY$|"
         r"^ASIAN HISTORY$|^AFRICAN HISTORY$|^THE FRENCH REVOLUTION$|"
         r"^HISTORIC NAMES?$|PEOPLE IN HISTORY|"
         r"^THE 20th CENTURY$|^THE 20TH CENTURY$|^THE 19th CENTURY$|"
         r"^THE 17th CENTURY$|^THE 18th CENTURY$|"
         r"^THE 1930s$|^THE 1940s$|^THE 1950s$|^THE 1960s$|^THE 1970s$|^THE 1980s$|^THE 1880s$|"
         r"^ANCIENT TIMES?$|^ANCIENT ROME$|^ANCIENT EGYPT$|^RECENT HISTORY$|"
         r"^ARCHAEOLOGY$|^WORLD LEADERS$|^TREATIES$|^EXPLORERS?$|"
         r"^TEENS IN HISTORY$|^WOMEN IN HISTORY$|^HISTORIC WOMEN$|"
         r"^20th CENTURY WOMEN$|^WORLD POLITICS$"),

        ("Royalty & Rulers",
         r"^ROYALTY$|KINGS & QUEENS|^BRITISH ROYALTY$|^RULERS?$|^MONARCHS?$"),

        ("The Bible & Religion",
         r"^THE BIBLE$|^RELIGION$|THE OLD TESTAMENT|^OLD TESTAMENT$|"
         r"THE NEW TESTAMENT|^NEW TESTAMENT$|^SAINTS?$|^BIBLICAL|"
         r"^BOOKS OF THE BIBLE$|^GENESIS$|WORLD RELIGION|RELIGIOUS LEADERS"),

        ("Mythology",
         r"^MYTHOLOGY$|GREEK MYTHOLOGY|NORSE MYTHOLOGY|MYTHS? & LEGENDS|CLASSICAL MYTHOLOGY"),

        ("Literature",
         r"^LITERATURE$|^AUTHORS?$|AMERICAN LITERATURE|ENGLISH LITERATURE|"
         r"WORLD LITERATURE|WOMEN AUTHORS|BRITISH AUTHORS|^NOVELISTS?$|"
         r"^NOVELS?$|NOVELS? & NOVELISTS?|^FICTION$|HISTORICAL FICTION|"
         r"20th CENTURY NOVELS?|19th CENTURY LIT|LITERARY HODGE|LITERARY QUOTES|"
         r"WOMEN WRITERS|^BRIT LIT$|NOVEL CHARACTERS|^BIOGRAPHIES$|^LIBRARIES$|"
         r"^PEN NAMES$|^AMERICAN AUTHORS$|^AMERICAN LITERATURE$"),

        ("Poetry, Plays & Theatre",
         r"POETS? & POETRY|^POETS?$|^SHAKESPEARE|SHAKESPEAREAN|"
         r"^PLAYS?$|PLAYS? & PLAYWRIGHTS?|^PLAYWRIGHTS?$|"
         r"^THEATRE$|^THEATER$|^DRAMA$|CHARACTERS IN MUSICALS?|^MUSICALS?$"),

        ("Visual Arts",
         r"^ART$|^ARTISTS?$|ART & ARTISTS|ARTISTS? & THEIR|^SCULPTURE$|"
         r"^MUSEUMS?$|^ARCHITECT|ART HISTORY"),

        ("Classical Music & Opera",
         r"^COMPOSERS?$|CLASSICAL COMPOSERS?|^OPERA$|^BALLET$"),

        ("Science & Elements",
         r"^THE ELEMENTS?$|^ELEMENTS? OF|ROCKS & MINERALS|^METALS?$|"
         r"^GEMS?$|^AGRICULTURE$|PERIODIC TABLE|^MINERALS?$"),

        ("Astronomy & Space",
         r"^ASTRONOMY$|THE PLANETS?$|SPACE EXPLORATION|^THE SOLAR SYSTEM$|"
         r"^CONSTELLATIONS?$|^ASTROLOGY$|^MAN IN SPACE$|^SPACE$"),

        ("Languages",
         r"^LANGUAGES?$|OFFICIAL LANGUAGES?"),

        ("Colleges & Education",
         r"COLLEGES? & UNIVERSITIES|^COLLEGES?$|^UNIVERSITIES$|^COLLEGE TOWNS$"),

        ("Sports & Olympics",
         r"^OLYMPICS?$|OLYMPIC HISTORY|OLYMPIC MEDALISTS?|"
         r"^BASEBALL$|^FOOTBALL$|^BASKETBALL$|^TENNIS$|^GOLF$|"
         r"^BOXING$|^SWIMMING$|^TRACK & FIELD$|^SOCCER$|^HOCKEY$|"
         r"^SPORTS?$|SPORTS HOME CITIES"),

        ("Food & Drink",
         r"POTENT POTABLES|^WINE$|INTERNATIONAL FOOD|^FOOD$|^COOKING$|^CUISINE$"),

        ("Holidays & Observances",
         r"HOLIDAYS? & OBSERVANCES?|^ANNUAL EVENTS$|^HOLIDAYS?$|^THE CALENDAR$|^MONTHS?$"),

        ("Travel & Landmarks",
         r"^TRAVEL & TOURISM$|^LANDMARKS?$|^AIRPORTS?$|^BRIDGES?$|"
         r"^HIGHWAYS? & BYWAYS$|^PARKS$|^HISTORIC HOMES?$|^FORESTS?$|"
         r"WORLD CAPITAL ATTRACT"),

        ("Notable People & Quotes",
         r"^FAMOUS NAMES$|^FAMOUS WOMEN$|^NOTABLE NAMES$|^NOTABLE WOMEN$|"
         r"^QUOTABLE WOMEN$|^QUOTATIONS?$|^QUOTES?$|^HISTORIC QUOTES$|"
         r"^POLITICAL QUOTES?$|^NOTORIOUS$"),

        ("Colors, Numbers & Symbols",
         r"^COLORS?$|^COINS?$|^FLAGS?$|^MEDALS? & DECORATIONS$|"
         r"^NICKNAMES?$|^AWARDS?$|^NUMBER, PLEASE$|^MONEY$"),
    ]

    # ── Assign each eligible category to its domain(s) ───────────────────
    domains: dict = {}
    categorized: set = set()
    for domain_name, pattern in DOMAIN_PATTERNS:
        members = [
            c for c in analysis_lists
            if _re.search(pattern, c)
        ]
        # Sort by matched answer count descending
        members.sort(key=lambda c: match_count.get(c, 0), reverse=True)
        if members:
            domains[domain_name] = members
            categorized.update(members)

    # Uncategorized eligible categories → "General & Mixed" domain
    uncategorized = [
        c for c in analysis_lists if c not in categorized
    ]
    uncategorized.sort(key=lambda c: match_count.get(c, 0), reverse=True)
    if uncategorized:
        domains["General & Mixed"] = uncategorized

    lists_json   = _json.dumps(analysis_lists, ensure_ascii=False, separators=(",", ":"))
    domains_json = _json.dumps(domains,        ensure_ascii=False, separators=(",", ":"))
    return lists_json, domains_json


def _write_html_index(answer_map: dict, cat_map: dict) -> None:
    """Write an interactive HTML flashcard browser with category filtering."""
    import pandas as pd

    out_path = cfg.ROOT / "flashcards.html"

    def _make_js_data(name_list: list[str], subdir: str) -> str:
        items = [
            {"n": name, "s": f"output/cards/{subdir}/{_safe_filename(name)}.png"}
            for name in sorted(name_list, key=str.casefold)
        ]
        return json.dumps(items, ensure_ascii=False, separators=(",", ":"))

    def _make_cat_answers(df_: pd.DataFrame) -> str:
        cat_set = set(cat_map.keys())
        ans_set = set(answer_map.keys())
        filt = df_[df_["category"].isin(cat_set) & df_["answer"].isin(ans_set)]
        mapping = (
            filt.groupby("category")["answer"]
            .apply(lambda x: sorted(x.unique().tolist()))
            .to_dict()
        )
        return json.dumps(mapping, ensure_ascii=False, separators=(",", ":"))

    log.info("  Loading parquet to build category->answers map ...")
    df = pd.read_parquet(cfg.CLUES_PARQUET, columns=["category", "answer"])

    log.info("  Building curated study lists ...")
    lists_json, domains_json = _build_list_analysis(df, answer_map)

    html = (
        _HTML_TEMPLATE
        .replace("__ANSWERS_JSON__",        _make_js_data(list(answer_map.keys()), "answers"))
        .replace("__CATS_JSON__",           _make_js_data(list(cat_map.keys()),    "categories"))
        .replace("__CAT_ANSWERS_JSON__",    _make_cat_answers(df))
        .replace("__ANALYSIS_LISTS_JSON__", lists_json)
        .replace("__DOMAINS_JSON__",        domains_json)
    )
    out_path.write_text(html, encoding="utf-8")
    log.info("HTML index written -> %s", out_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    generate_cards(force=False)
