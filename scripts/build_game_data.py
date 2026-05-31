#!/usr/bin/env python3
"""
build_game_data.py – Build the Jeopardy! Quiz Game data JSON.

Reads the combined season TSV, selects high-quality clues,
and outputs data/processed/game_data.json for the PWA game.

Output format:
{
  "categories": [
    {
      "id": 0,
      "name": "HISTORY",
      "clues": [
        {"v": 200, "q": "clue text shown on board", "a": "correct response"},
        ...  (5 clues, values 200/400/600/800/1000)
      ]
    },
    ...
  ],
  "final": [
    {"category": "POTPOURRI", "q": "...", "a": "..."},
    ...
  ]
}
"""

import csv
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TSV  = ROOT / "data" / "raw" / "combined_season1-41.tsv"
OUT  = ROOT / "data" / "processed" / "game_data.json"

random.seed(42)

# Value normalization: map any dollar value to 1-5 rank
# Early seasons use 100/200/300/400/500; later use 200/400/600/800/1000
VALUE_RANKS = {
    100: 1, 200: 1,
    200: 2, 400: 2,
    300: 3, 600: 3,
    400: 4, 800: 4,
    500: 5, 1000: 5,
}

RANK_TO_VALUE = {1: 200, 2: 400, 3: 600, 4: 800, 5: 1000}


def clean_text(s: str) -> str:
    """Remove HTML tags and extra whitespace."""
    s = re.sub(r'<[^>]+>', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def value_rank(val_str: str) -> int | None:
    try:
        v = int(val_str.replace(',', '').replace('$', '').strip())
    except (ValueError, AttributeError):
        return None
    # Map to rank 1-5
    if v in (100, 200):  return 1
    if v in (200, 400):  return 2
    if v in (300, 600):  return 3
    if v in (400, 800):  return 4
    if v in (500, 1000): return 5
    # Some oddball values
    if v <= 250:   return 1
    if v <= 450:   return 2
    if v <= 650:   return 3
    if v <= 850:   return 4
    if v <= 1200:  return 5
    return None


def is_good_clue(q: str, a: str) -> bool:
    """Return True if the clue is suitable for the game."""
    if not q or not a:
        return False
    if len(q) < 15 or len(q) > 400:
        return False
    if len(a) < 1 or len(a) > 120:
        return False
    # Skip video/audio clues
    for marker in ('seen here', 'heard here', 'shown here', 'video', 'audio',
                   'this man', 'this woman', 'this person', '<a', 'href='):
        if marker in q.lower():
            return False
    return True


def main():
    print("Reading TSV …")
    by_cat: dict[str, dict[int, list[dict]]] = defaultdict(lambda: defaultdict(list))
    final_pool: list[dict] = []
    total = 0

    with open(TSV, encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            total += 1
            rnd = row.get('round', '').strip()

            q_text = clean_text(row.get('answer', ''))   # clue shown on board
            a_text = clean_text(row.get('question', '')) # correct response
            cat    = row.get('category', '').strip().upper()

            if not cat or not q_text or not a_text:
                continue

            # Final Jeopardy
            if rnd == '3':
                if is_good_clue(q_text, a_text):
                    final_pool.append({'category': cat, 'q': q_text, 'a': a_text})
                continue

            rank = value_rank(row.get('clue_value', ''))
            if rank is None:
                continue

            if not is_good_clue(q_text, a_text):
                continue

            by_cat[cat][rank].append({'q': q_text, 'a': a_text})

    print(f"Read {total:,} rows. Found {len(by_cat):,} categories.")

    # Build category pool: keep cats with at least 1 clue at each rank 1-5
    # Pick one clue per rank (random sampling ensures variety across games)
    valid_cats = []
    for cat, ranks in by_cat.items():
        if not all(r in ranks for r in range(1, 6)):
            continue
        clues = []
        for r in range(1, 6):
            options = ranks[r]
            clue = random.choice(options)
            clues.append({
                'v': RANK_TO_VALUE[r],
                'q': clue['q'],
                'a': clue['a'],
            })
        valid_cats.append({'name': cat, 'clues': clues})

    print(f"Valid categories (5 ranks each): {len(valid_cats):,}")

    # Shuffle and keep up to 1200 for the game pool
    random.shuffle(valid_cats)
    valid_cats = valid_cats[:1200]

    # Add numeric IDs
    for i, cat in enumerate(valid_cats):
        cat['id'] = i

    # Final Jeopardy pool (up to 200)
    random.shuffle(final_pool)
    final_pool = final_pool[:200]

    out = {'categories': valid_cats, 'final': final_pool}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, separators=(',', ':'), ensure_ascii=False)

    size_kb = OUT.stat().st_size / 1024
    print(f"Wrote {OUT} ({len(valid_cats)} categories, {len(final_pool)} finals, {size_kb:.0f} KB)")


if __name__ == '__main__':
    main()
