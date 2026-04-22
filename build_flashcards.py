"""
build_flashcards.py  –  Generate data/processed/flashcards.json

For each top-1500 answer, collects the actual Jeopardy clue texts from
the dataset and distils them into a structured flashcard:
  {
    answer: "Australia",
    categories: ["Geography", "History", ...],
    clues: [
      {"cat": "GEOGRAPHY", "text": "2 of its states are Victoria & Queensland"},
      ...
    ]
  }

The JSON structure written is:
  { "answer_name": {clues, categories, total_clues}, ... }

Run from project root:
  python build_flashcards.py
"""
import json, re, pathlib, sys

ROOT    = pathlib.Path(__file__).parent
PARQUET = ROOT / "data/processed/clues_cleaned.parquet"
ANS_JSON = ROOT / "data/processed/associations_answers.json"
OUT     = ROOT / "data/processed/flashcards.json"

import pandas as pd

print("Loading parquet...")
df = pd.read_parquet(PARQUET, columns=["answer", "clue", "category", "round", "air_date"])

print("Loading answer map...")
with open(ANS_JSON, encoding="utf-8") as f:
    answer_map = json.load(f)

ans_set = set(answer_map.keys())
print(f"{len(ans_set)} top answers")

# ── Filter to top-1500 answers only ──────────────────────────────────────────
df = df[df["answer"].isin(ans_set)].copy()

# ── Clean clue text ───────────────────────────────────────────────────────────
def clean_clue(text: str) -> str:
    """Strip HTML tags and normalise whitespace."""
    text = re.sub(r"<[^>]+>", "", str(text))
    text = re.sub(r"\s+", " ", text).strip()
    return text

df["clue_clean"] = df["clue"].apply(clean_clue)
# Drop empty / very short clues
df = df[df["clue_clean"].str.len() >= 20]

# ── Score clues by informativeness ───────────────────────────────────────────
# Prefer higher-dollar (round 2 > round 1), and more specific categories.
# We use a simple heuristic: Double Jeopardy clues tend to be more specific.
df["score"] = df["round"].apply(lambda r: 2 if r == 2 else 1)

# ── Build flashcard per answer ────────────────────────────────────────────────
print("Building flashcard data...")
flashcards = {}

for answer, group in df.groupby("answer"):
    # Deduplicate clue text (exact)
    seen = set()
    rows = []
    for _, r in group.sort_values("score", ascending=False).iterrows():
        txt = r["clue_clean"]
        if txt.lower() in seen:
            continue
        seen.add(txt.lower())
        rows.append({"cat": r["category"], "text": txt})

    # Keep up to 12 most representative clues, spread across categories
    # Strategy: pick at most 2 per category, then fill up to 12
    cat_counts: dict = {}
    selected = []
    for row in rows:
        c = row["cat"]
        if cat_counts.get(c, 0) < 2:
            selected.append(row)
            cat_counts[c] = cat_counts.get(c, 0) + 1
        if len(selected) >= 12:
            break
    # If we got fewer than 12, fill from the remainder
    if len(selected) < 12:
        for row in rows:
            if row not in selected:
                selected.append(row)
            if len(selected) >= 12:
                break

    unique_cats = sorted(set(r["cat"] for r in selected))
    flashcards[answer] = {
        "clues": selected,
        "categories": unique_cats,
        "total_clues": len(group),
    }

print(f"Built {len(flashcards)} flashcards")
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(flashcards, f, ensure_ascii=False, separators=(",", ":"))

size_mb = OUT.stat().st_size / 1_048_576
print(f"Written to {OUT}  ({size_mb:.1f} MB)")
