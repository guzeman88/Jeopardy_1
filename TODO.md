# Jeopardy Word-Cloud Project — Solo Dev TODO

> Colin Davy's method: scrape/download ~538k clues, clean with NLTK,
> build word-frequency maps per answer & category, generate PNG "word map"
> flashcards for Pavlov-style recall training.
>
> Reference: [How I Won Jeopardy With Data Science](https://colindavy.medium.com/how-i-won-jeopardy-with-data-science-c2e9b52a1958)

---

## Setup

- [x] Create project directory `Jeopardy_1/`
- [x] Create virtual environment (`python -m venv venv`)
- [ ] Activate venv and install dependencies: `pip install -r requirements.txt`
- [ ] Download NLTK data (auto-runs on first pipeline execution, or manually):
  ```python
  import nltk; nltk.download(['stopwords', 'punkt', 'wordnet'])
  ```

---

## 1. Data Acquisition

- [ ] Go to: https://github.com/jwolle1/jeopardy_clue_dataset/releases
- [ ] Download latest release (Season 1-41 combined, ~538k clues)
- [ ] Unzip and place file in `data/raw/`
- [ ] Verify row count: `python -c "import pandas as pd; print(len(pd.read_csv('data/raw/<filename>')))"` — expect ~538,000

---

## 2. Project Structure (already scaffolded)

- [x] `src/config.py` — central paths + constants
- [x] `src/data_loader.py` — load & normalize raw CSV/TSV
- [x] `src/preprocessing.py` — NLP cleaning (lowercase, stopwords, stemming)
- [x] `src/associations.py` — word-freq maps per answer & category
- [x] `src/wordcloud_generator.py` — render PNG cards + HTML viewer
- [x] `scripts/run_pipeline.py` — CLI orchestrator
- [x] `requirements.txt`
- [x] `.gitignore`
- [x] `README.md`

---

## 3. Run the Pipeline

- [ ] Run full pipeline:
  ```bash
  python scripts/run_pipeline.py
  ```
- [ ] Confirm `data/processed/clues_cleaned.parquet` was created
- [ ] Confirm `data/processed/associations_answers.json` was created
- [ ] Confirm `data/processed/associations_categories.json` was created
- [ ] Confirm PNG cards exist in `output/cards/answers/` and `output/cards/categories/`
- [ ] Open `flashcards.html` in a browser — verify cards display correctly

---

## 4. Spot-Check Quality

- [ ] Check word cloud for **Shakespeare** — expect: play, write, william, hamlet, tragedy, etc.
- [ ] Check word cloud for **Washington** — expect: george, president, dc, state, cherry, etc.
- [ ] Check word cloud for **Solomon** — expect: wise, king, bible, temple, proverb, israel, etc.
- [ ] Check a category cloud (e.g., **WORLD CAPITALS**) — expect city/country names
- [ ] Review `output/stats/top_answers.csv` — confirm expected high-frequency answers at top

---

## 5. Optional Improvements

- [ ] Export top cards to **Anki** deck (use `genanki` library)
- [ ] Add **TF-IDF** scoring as alternative to raw counts (better for short-tail answers)
- [ ] Add **trigram** support in `config.py` → `USE_TRIGRAMS = True`
- [ ] Build a simple **Streamlit** quiz UI: show word cloud, guess the answer
- [ ] Add `--category_filter` flag to pipeline for targeted category study
- [ ] Schedule a weekly re-run to pick up new J-Archive seasons

---

## 6. Git / Backup

- [ ] `git init` (if not already done)
- [ ] Initial commit: source files only (data/ and output/ are gitignored)
- [ ] Push to private GitHub repo for backup

---

## Notes

- Pipeline is **idempotent** — safe to re-run; cached stages are skipped.
- Use `--force` to re-process everything, `--regen_clouds` to only redo PNGs.
- All tuneable constants live in `src/config.py` — no need to edit other files.
- Estimated runtime on first full run: ~5-15 min depending on machine (NLP processing is the bottleneck).
