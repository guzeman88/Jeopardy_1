#!/usr/bin/env python3
"""
run_pipeline.py – Full Jeopardy word-cloud pipeline.

Usage
-----
# Run all steps (skips stages already cached on disk):
python scripts/run_pipeline.py

# Force re-run of every stage:
python scripts/run_pipeline.py --force

# Override key settings at runtime:
python scripts/run_pipeline.py --min_freq 15 --top_n 500 --regen_clouds
"""
import argparse
import logging
import sys
import time
from pathlib import Path

# Make sure the project root is on sys.path so `src` imports work.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import src.config as cfg
from src import preprocessing, associations
from src.wordcloud_generator import generate_cards

# ── Logging setup ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Jeopardy word-cloud pipeline")
    p.add_argument("--force",        action="store_true",
                   help="Re-run all stages even if cached output exists.")
    p.add_argument("--regen_clouds", action="store_true",
                   help="Regenerate PNG cards even if they already exist "
                        "(faster than --force when data is already processed).")
    p.add_argument("--min_freq",  type=int, default=None,
                   help=f"Min answer frequency for a card (default: {cfg.MIN_ANSWER_FREQ})")
    p.add_argument("--top_n",     type=int, default=None,
                   help=f"Max number of answer cards (default: {cfg.TOP_N_ANSWERS})")
    p.add_argument("--no_bigrams", action="store_true",
                   help="Disable bigram counting (unigrams only).")
    return p.parse_args()


def _apply_overrides(args: argparse.Namespace) -> None:
    if args.min_freq  is not None: cfg.MIN_ANSWER_FREQ = args.min_freq
    if args.top_n     is not None: cfg.TOP_N_ANSWERS   = args.top_n
    if args.no_bigrams:            cfg.USE_BIGRAMS      = False


def main() -> None:
    args = _parse_args()
    _apply_overrides(args)
    t0 = time.perf_counter()

    log.info("=" * 60)
    log.info("  JEOPARDY WORD-CLOUD PIPELINE  (Colin Davy method)")
    log.info("=" * 60)
    log.info("Settings: min_freq=%d  top_n=%d  bigrams=%s",
             cfg.MIN_ANSWER_FREQ, cfg.TOP_N_ANSWERS, cfg.USE_BIGRAMS)

    # ── Step 1: Preprocess ────────────────────────────────────────────────
    log.info("")
    log.info("STEP 1/3 — Preprocessing")
    preprocessing.run(force=args.force)

    # ── Step 2: Build associations ────────────────────────────────────────
    log.info("")
    log.info("STEP 2/3 — Building associations")
    associations.run(force=args.force)

    # ── Step 3: Generate word-cloud cards ─────────────────────────────────
    log.info("")
    log.info("STEP 3/3 — Generating word-cloud cards")
    generate_cards(force=args.force or args.regen_clouds)

    elapsed = time.perf_counter() - t0
    log.info("")
    log.info("Done in %.1f s.", elapsed)
    log.info("Open flashcards.html in your browser to browse the cards.")


if __name__ == "__main__":
    main()
