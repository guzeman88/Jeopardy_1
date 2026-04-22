# Jeopardy! Word-Cloud Study System

Replication of Colin Davy's data-science prep method from his article
[*How I Won Jeopardy With Data Science*](https://colindavy.medium.com/how-i-won-jeopardy-with-data-science-c2e9b52a1958).

The pipeline turns ~538,000 historical Jeopardy! clues into visual "word map"
flashcards: one PNG per high-frequency answer and category. The largest words
in each cloud are the strongest Pavlov triggers — the words that most reliably
appear in clues for that answer.

---

## Quick Start

### 1. Install dependencies
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Download the dataset
Go to the [jwolle1/jeopardy_clue_dataset releases page](https://github.com/jwolle1/jeopardy_clue_dataset/releases)
and download the latest combined TSV/CSV (Season 1-41, ~538k clues).
Place the file in `data/raw/`.

### 3. Run the pipeline
```bash
python scripts/run_pipeline.py
```

That's it. The script will:
1. Load and clean the raw data → `data/processed/clues_cleaned.parquet`
2. Build word-frequency associations per answer and category → `data/processed/associations_*.json`
3. Generate PNG word-cloud cards → `output/cards/answers/` and `output/cards/categories/`
4. Write `flashcards.html` – open in any browser to browse all cards with a search filter.

### Optional flags
```bash
# Force re-run of every stage (ignore cache):
python scripts/run_pipeline.py --force

# Regenerate PNGs only (data already processed):
python scripts/run_pipeline.py --regen_clouds

# Custom settings:
python scripts/run_pipeline.py --min_freq 20 --top_n 500
```

---

## Project Structure

```
Jeopardy_1/
├── data/
│   ├── raw/                        # place downloaded dataset here
│   └── processed/                  # auto-generated parquet + JSON
├── src/
│   ├── config.py                   # all tuneable constants/paths
│   ├── data_loader.py              # load + normalize raw CSV/TSV
│   ├── preprocessing.py            # NLP: lowercase, stopwords, stemming
│   ├── associations.py             # build word-freq maps per answer/category
│   └── wordcloud_generator.py      # render PNGs + write flashcards.html
├── scripts/
│   └── run_pipeline.py             # CLI entrypoint (orchestrates all steps)
├── output/
│   ├── cards/answers/              # answer PNGs
│   ├── cards/categories/           # category PNGs
│   └── stats/                      # top_answers.csv, summary.json, etc.
├── notebooks/
│   └── 01_eda.ipynb                # optional EDA scratch space
├── flashcards.html                 # auto-generated browser viewer
├── requirements.txt
└── README.md
```

---

## Tuning (`src/config.py`)

| Constant | Default | Meaning |
|---|---|---|
| `MIN_ANSWER_FREQ` | 10 | Min times an answer must appear to get a card |
| `TOP_N_ANSWERS` | 1500 | Max number of answer cards generated |
| `MIN_CAT_FREQ` | 20 | Min times a category must appear |
| `USE_BIGRAMS` | True | Include 2-word phrases in frequency counts |
| `WC_MAX_WORDS` | 100 | Words shown per cloud |
| `WC_COLORMAP` | viridis | Any matplotlib colormap name |
| `EXTRA_STOPWORDS` | (set) | Additional words to remove beyond NLTK defaults |

---

## NLP Pipeline (Colin Davy's exact method)

1. Decode HTML entities (`&amp;` → `&`)
2. Strip HTML tags (`<i>`, `<a href=...>`, etc.)
3. Lowercase
4. Remove punctuation
5. Remove standalone numbers
6. Tokenize (whitespace split)
7. Remove stopwords (NLTK English + custom extras)
8. Porter stemming

Example:
> *"The book of Ecclesiastes is traditionally ascribed to this wise king"*
>
> → `book ecclesiast tradit ascrib wise king`

---

## Output

After a full run you will have:
- ~1,500 answer word-cloud PNGs (e.g., `Shakespeare.png`, `Washington.png`)
- Hundreds of category word-cloud PNGs
- `flashcards.html` – searchable browser-based viewer
- `output/stats/top_answers.csv` – ranked list of most common answers
- `output/stats/summary.json` – pipeline run summary

---

## Credit

Method and inspiration: Colin Davy (Jeopardy! Season 37 contestant)
Data: [jwolle1/jeopardy_clue_dataset](https://github.com/jwolle1/jeopardy_clue_dataset)
