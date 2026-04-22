"""
NLP preprocessing – exactly Colin Davy's method:
  1. Lowercase + strip HTML entities
  2. Remove punctuation
  3. Tokenize
  4. Remove English stopwords + custom extras
  5. Porter stemming

Produces a 'cleaned_clue' column and saves the DataFrame as Parquet.
"""
import html
import logging
import re

import nltk
import pandas as pd
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from tqdm import tqdm

from . import config as cfg
from .data_loader import load_raw

log = logging.getLogger(__name__)

# ── NLTK resources (download once if missing) ──────────────────────────────
def _ensure_nltk():
    for resource in ("stopwords", "punkt", "wordnet"):
        try:
            nltk.data.find(f"corpora/{resource}" if resource != "punkt" else f"tokenizers/{resource}")
        except LookupError:
            log.info("Downloading NLTK resource: %s", resource)
            nltk.download(resource, quiet=True)


_ensure_nltk()

_stemmer    = PorterStemmer()
_stop_words = set(stopwords.words("english")) | cfg.EXTRA_STOPWORDS

# Pre-compiled regex
_RE_HTML_TAG = re.compile(r"<[^>]+>")          # strip <i>, <a href=...>, etc.
_RE_PUNCT    = re.compile(r"[^\w\s]")           # remove all non-word, non-space
_RE_DIGITS   = re.compile(r"\b\d+\b")           # remove standalone numbers


def clean_clue(text: str) -> str:
    """
    Return a space-joined string of stemmed, stop-word-free tokens.
    Empty string if nothing meaningful remains.
    """
    # 1. Decode HTML entities  (&amp; → &, etc.)
    text = html.unescape(text)
    # 2. Remove HTML tags
    text = _RE_HTML_TAG.sub(" ", text)
    # 3. Lowercase
    text = text.lower()
    # 4. Remove punctuation
    text = _RE_PUNCT.sub(" ", text)
    # 5. Remove lone digits (years as lone tokens add noise)
    text = _RE_DIGITS.sub(" ", text)
    # 6. Tokenize (simple split – faster than nltk.word_tokenize at scale)
    tokens = text.split()
    # 7. Remove stop words and very short tokens
    tokens = [t for t in tokens if t not in _stop_words and len(t) > 1]
    # 8. Stem
    tokens = [_stemmer.stem(t) for t in tokens]
    return " ".join(tokens)


def run(force: bool = False) -> pd.DataFrame:
    """
    Load raw data, apply cleaning, save to parquet, return DataFrame.

    Parameters
    ----------
    force : bool
        Re-process even if the parquet already exists.
    """
    cfg.DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if cfg.CLUES_PARQUET.exists() and not force:
        log.info("Processed parquet already exists. Loading from cache.")
        return pd.read_parquet(cfg.CLUES_PARQUET)

    df = load_raw()

    log.info("Cleaning %d clues (this may take a minute) ...", len(df))
    tqdm.pandas(desc="Cleaning clues")
    df["cleaned_clue"] = df["clue"].progress_apply(clean_clue)

    # Drop rows where cleaning produced an empty string
    before = len(df)
    df = df[df["cleaned_clue"].str.len() > 0].reset_index(drop=True)
    log.info("  Dropped %d rows where cleaned clue is empty.", before - len(df))

    df.to_parquet(cfg.CLUES_PARQUET, index=False)
    log.info("Saved processed data → %s  (%d rows)", cfg.CLUES_PARQUET, len(df))
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run(force=True)
