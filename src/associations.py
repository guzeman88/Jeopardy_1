"""
Build word/phrase frequency maps per answer and per category.

For every answer (or category) that meets the minimum-frequency threshold,
this module counts how often each stemmed word (and optionally bigram) appears
across all clues for that answer/category.

Output: two JSON files (dicts of {term: count}).
"""
import json
import logging
from collections import Counter, defaultdict

import pandas as pd
from tqdm import tqdm

from . import config as cfg
from .data_loader import load_processed

log = logging.getLogger(__name__)


def _build_map(
    df: pd.DataFrame,
    group_col: str,
    min_freq: int,
    top_n: int | None,
    use_bigrams: bool,
) -> dict[str, dict[str, int]]:
    """
    Group df by group_col, count word (+ bigram) frequencies per group.

    Returns
    -------
    dict[str, dict[str, int]]
        {group_value: {term: count, ...}, ...}
    """
    # Count how often each group appears
    freq = df[group_col].value_counts()
    eligible = freq[freq >= min_freq]

    if top_n:
        eligible = eligible.head(top_n)

    log.info(
        "  %s: %d unique values, %d eligible (freq >= %d, top_n=%s)",
        group_col, len(freq), len(eligible), min_freq, top_n,
    )

    result: dict[str, dict[str, int]] = {}

    for group_val in tqdm(eligible.index, desc=f"Building {group_col} associations"):
        subset = df.loc[df[group_col] == group_val, "cleaned_clue"]
        counter: Counter = Counter()

        for clue in subset:
            tokens = clue.split()
            counter.update(tokens)

            if use_bigrams:
                bigrams = [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)]
                counter.update(bigrams)

        if counter:
            result[group_val] = dict(counter.most_common())  # most common first

    return result


def _save_json(data: dict, path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info("Saved %d entries → %s", len(data), path)


def load_json(path) -> dict[str, dict[str, int]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run(force: bool = False) -> tuple[dict, dict]:
    """
    Build and persist answer + category association maps.

    Returns (answer_map, category_map).
    """
    cfg.DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if (
        cfg.ASSOC_ANSWERS_JSON.exists()
        and cfg.ASSOC_CATS_JSON.exists()
        and not force
    ):
        log.info("Association JSONs already exist. Loading from cache.")
        return load_json(cfg.ASSOC_ANSWERS_JSON), load_json(cfg.ASSOC_CATS_JSON)

    df = load_processed()
    log.info("Building answer associations ...")
    answer_map = _build_map(
        df,
        group_col="answer",
        min_freq=cfg.MIN_ANSWER_FREQ,
        top_n=cfg.TOP_N_ANSWERS,
        use_bigrams=cfg.USE_BIGRAMS,
    )

    log.info("Building category associations ...")
    cat_map = _build_map(
        df,
        group_col="category",
        min_freq=cfg.MIN_CAT_FREQ,
        top_n=None,
        use_bigrams=cfg.USE_BIGRAMS,
    )

    _save_json(answer_map, cfg.ASSOC_ANSWERS_JSON)
    _save_json(cat_map, cfg.ASSOC_CATS_JSON)

    # Save summary stats
    _write_stats(df, answer_map, cat_map)

    return answer_map, cat_map


def _write_stats(df: pd.DataFrame, answer_map: dict, cat_map: dict) -> None:
    cfg.OUTPUT_STATS_DIR.mkdir(parents=True, exist_ok=True)

    top_answers = df["answer"].value_counts().head(50).reset_index()
    top_answers.columns = ["answer", "count"]
    top_answers.to_csv(cfg.OUTPUT_STATS_DIR / "top_answers.csv", index=False)

    top_cats = df["category"].value_counts().head(50).reset_index()
    top_cats.columns = ["category", "count"]
    top_cats.to_csv(cfg.OUTPUT_STATS_DIR / "top_categories.csv", index=False)

    summary = {
        "total_clues"      : int(len(df)),
        "unique_answers"   : int(df["answer"].nunique()),
        "unique_categories": int(df["category"].nunique()),
        "answer_cards"     : len(answer_map),
        "category_cards"   : len(cat_map),
    }
    with open(cfg.OUTPUT_STATS_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    log.info("Stats written to %s", cfg.OUTPUT_STATS_DIR)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run(force=True)
