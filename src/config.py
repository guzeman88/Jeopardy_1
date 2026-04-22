"""
Central configuration for the Jeopardy word-cloud pipeline.
Edit the paths and constants here; everything else imports from this file.
"""
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent

DATA_RAW_DIR       = ROOT / "data" / "raw"
DATA_PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUT_ANSWERS_DIR = ROOT / "output" / "cards" / "answers"
OUTPUT_CATS_DIR    = ROOT / "output" / "cards" / "categories"
OUTPUT_STATS_DIR   = ROOT / "output" / "stats"

# Processed parquet paths
CLUES_PARQUET      = DATA_PROCESSED_DIR / "clues_cleaned.parquet"
ASSOC_ANSWERS_JSON = DATA_PROCESSED_DIR / "associations_answers.json"
ASSOC_CATS_JSON    = DATA_PROCESSED_DIR / "associations_categories.json"

# ── Raw data ───────────────────────────────────────────────────────────────
# Place the downloaded TSV/CSV from jwolle1/jeopardy_clue_dataset here.
# The pipeline will auto-detect .tsv / .csv files in DATA_RAW_DIR.
RAW_FILENAME = None   # set to e.g. "combined_season1-41.tsv" to be explicit

# ── NLP settings ──────────────────────────────────────────────────────────
EXTRA_STOPWORDS: set[str] = {
    "one", "two", "three", "first", "last", "new", "old",
    "called", "known", "name", "type", "kind", "term",
    "also", "often", "used", "use", "made", "make",
}

USE_BIGRAMS = True   # include 2-word phrases in association counts

# ── Association filters ───────────────────────────────────────────────────
MIN_ANSWER_FREQ  = 10   # minimum times an answer must appear to get a card
TOP_N_ANSWERS    = 1500 # cap: only generate cards for top-N answers by freq
MIN_CAT_FREQ     = 20   # minimum times a category must appear

# ── Word-cloud appearance ─────────────────────────────────────────────────
WC_WIDTH      = 900
WC_HEIGHT     = 450
WC_MAX_WORDS  = 100
WC_BG_COLOR   = "white"
WC_COLORMAP   = "viridis"   # any matplotlib colormap name
WC_DPI        = 150
