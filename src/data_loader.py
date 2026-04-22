"""
Load and lightly normalize the raw Jeopardy clue dataset.

Supported input: any .tsv or .csv file in data/raw/.
Expected columns (case-insensitive):  category, clue, answer
Optional columns retained if present: value, season, show_number, air_date, round
"""
import logging
from pathlib import Path

import pandas as pd

from . import config as cfg

log = logging.getLogger(__name__)

# Columns we actually care about; everything else is dropped.
_REQUIRED = {"category", "clue", "answer"}
_OPTIONAL = {"value", "season", "show_number", "air_date", "round"}

# Common alternate column names in jwolle1 dataset and other public releases.
_ALIASES: dict[str, str] = {
    # jwolle1 dataset uses Jeopardy's own convention:
    #   "answer"   = the clue text displayed on the board (what Alex reads)
    #   "question" = the contestant's response (the actual answer, e.g. "Mongolia")
    # We flip them so our pipeline always has:
    #   clue   = the board clue text  (NLP input)
    #   answer = the contestant answer (grouping key for word clouds)
    "answer"         : "clue",
    "question"       : "answer",
    # alternate column names found in other public datasets
    "clue_text"      : "clue",
    "answer_text"    : "answer",
    "correct_response": "answer",
    "airdate"        : "air_date",
    "show #"         : "show_number",
    "show_#"         : "show_number",
    "dollar_value"   : "value",
}


def _detect_raw_file() -> Path:
    """Return the first .tsv or .csv found in DATA_RAW_DIR."""
    if cfg.RAW_FILENAME:
        path = cfg.DATA_RAW_DIR / cfg.RAW_FILENAME
        if not path.exists():
            raise FileNotFoundError(f"Configured RAW_FILENAME not found: {path}")
        return path

    for ext in ("*.tsv", "*.csv"):
        matches = sorted(cfg.DATA_RAW_DIR.glob(ext))
        if matches:
            log.info("Auto-detected raw file: %s", matches[0])
            return matches[0]

    raise FileNotFoundError(
        f"No .tsv or .csv file found in {cfg.DATA_RAW_DIR}.\n"
        "Download the dataset from https://github.com/jwolle1/jeopardy_clue_dataset "
        "and place it in data/raw/."
    )


def load_raw() -> pd.DataFrame:
    """
    Read the raw file, normalise column names, drop unusable rows,
    and return a tidy DataFrame with at minimum: category, clue, answer.
    """
    path = _detect_raw_file()
    sep = "\t" if path.suffix == ".tsv" else ","
    log.info("Loading %s ...", path.name)

    df = pd.read_csv(path, sep=sep, low_memory=False, on_bad_lines="skip")
    log.info("  Raw shape: %s", df.shape)

    # Normalize column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df.rename(columns=_ALIASES, inplace=True)

    # Verify required columns exist
    missing = _REQUIRED - set(df.columns)
    if missing:
        raise ValueError(
            f"Required columns missing after normalization: {missing}\n"
            f"Available columns: {list(df.columns)}"
        )

    # Keep only columns we use
    keep = list(_REQUIRED | (_OPTIONAL & set(df.columns)))
    df = df[keep].copy()

    # Drop rows missing the essentials
    before = len(df)
    df.dropna(subset=["clue", "answer"], inplace=True)
    df = df[df["clue"].str.strip().ne("") & df["answer"].str.strip().ne("")]
    log.info("  Dropped %d rows with null/empty clue or answer.", before - len(df))

    # Strip whitespace
    for col in ["category", "clue", "answer"]:
        df[col] = df[col].str.strip()

    # Deduplicate on (clue, answer) – exact duplicates only
    before = len(df)
    df.drop_duplicates(subset=["clue", "answer"], inplace=True)
    log.info("  Dropped %d exact duplicate clue+answer rows.", before - len(df))

    df.reset_index(drop=True, inplace=True)
    log.info("  Final shape: %s", df.shape)
    return df


def load_processed() -> pd.DataFrame:
    """Load the cleaned parquet produced by preprocessing.py."""
    if not cfg.CLUES_PARQUET.exists():
        raise FileNotFoundError(
            f"Processed parquet not found at {cfg.CLUES_PARQUET}. "
            "Run preprocessing first."
        )
    return pd.read_parquet(cfg.CLUES_PARQUET)
