# classify (Tafsir pipeline) - branch overview

This branch contains a lightweight pipeline that turns raw Tafsir texts (Arabic exegesis) stored in SQLite into consistently tagged XML using Google's Gemini (GUI automation or API), then serves the annotated corpus via a small FastAPI app.

## Repository layout

- `run_active_as_module.py` - helper to run the package as a module from anywhere.
- `Tafsir/config` - path & default settings (`BOOKS_DIR`, `ANNOTATED_DIR`, `DEFAULT_TAFSIR`).
- `Tafsir/pipeline/app.py` - FastAPI server that renders/searches the annotated Tafsir; auto-discovers source/annotated DBs.
- `Tafsir/pipeline/gemini_gui` - browser automation flow (pyautogui + OCR) to drive Gemini UI; core logic in `blocks_to_xml_gui.py`; prompt text in `gui_app_prompt.txt`.
- `Tafsir/pipeline/gemini_api` - API-based runner with the same guard/cleanup logic (`blocks_to_xml_api.py`).
- `Tafsir/pipeline/analysis` - CLI utilities for inspection and rollback diagnostics.
- `Tafsir/pipeline/static` - HTML/XML viewer assets the FastAPI app serves.
- `Tafsir/tafsir_books` - source SQLite DBs (each table named after the book, containing `id, text`).
- `Tafsir/tafsir_books_annotated` - generated annotated DBs (`<book>_annotated.sqlite3`) with section/block/chunk tables.
- `Tafsir/utils` - thin aliases (e.g., `blocks_to_xml_api.py` imports the GUI implementation to keep monkeypatches in sync).
- `Tafsir/logs` - structured JSON logs written by GUI/API automation and rollback tooling.

## Data model

- Source DB table: `<book>` with `id, text`.
- Annotated DB tables:
  - `tafsir_analysis_<book>`: `id`, XML in `extracted_text_full`, normalized text in `extracted_text_normalized`, timestamps.
  - `tafsir_analysis_<book>_blocks` / `_chunks`: block/chunk breakdown with FK back to sections.

## Guard logic (`evaluate_guard`)

Guard compares normalized source vs generated response tokens:

- `token_coverage = matched_source_tokens / source_token_count`
- `ngram_overlap = overlap(source_ngrams, response_ngrams) / source_ngrams`
- `length_ratio = min(len(source), len(response)) / max(len(source), len(response))`

Defaults:

- `GUARD_NGRAM_SIZE = 3` (clamped to available token length)
- `GUARD_MIN_LEN_RATIO = 0.5`
- `GUARD_MAX_RETRIES = 2`

Decision rules:

- `pass`: `token_coverage >= 0.85` and `ngram_overlap >= 0.6`
- `retry`: `token_coverage < 0.7` or `ngram_overlap < 0.4`
- `log`: borderline area between the thresholds
- hard override: if `length_ratio < 0.5`, decision is forced to `retry`

Runtime behavior:

- `retry` / `log` trigger re-ask attempts up to `GUARD_MAX_RETRIES + 1` total tries.
- If attempts are exhausted, the row is logged as `skip` and an empty section placeholder is inserted to keep ID alignment stable.

## Structured JSON logs

The pipeline now writes unified JSON files per model run:

- `Tafsir/logs/structured_logs_default.json`
- `Tafsir/logs/structured_logs_<model>.json`

Shape:

```json
{
  "512": {
    "progress": ["waiting for response", "guard borderline, retry attempt=1"],
    "guard": [
      {
        "decision": "retry",
        "attempt": 1,
        "criteria": {
          "coverage": 0.68,
          "overlap": 0.39,
          "length_ratio": 0.91
        },
        "thresholds": {
          "pass_coverage": 0.85,
          "pass_overlap": 0.6,
          "min_length_ratio": 0.5,
          "max_retries": 2
        },
        "reason": "coverage<0.85,overlap<0.6",
        "source": "row=512",
        "model_label": "default",
        "response": {
          "status": "rejected",
          "text": "..."
        }
      }
    ],
    "responses": ["response accepted, total_processed=120"],
    "errors": ["gemini request failed (...)"]
  }
}
```

Notes:

- Top-level keys are source row IDs as strings.
- Second-level keys are log buckets derived from logical log type (`guard`, `progress`, `responses`, `errors`).
- API guard entries are structured objects; GUI guard entries are currently string entries.

## Typical pipeline

1. Place a raw source DB in `Tafsir/tafsir_books/<book>.sqlite3` (table name `<book>`).
2. Generate annotations:
   - GUI route: run browser automation in `Tafsir/pipeline/gemini_gui/blocks_to_xml_gui.py`.
   - API route: `python -m Tafsir.pipeline.gemini_api.blocks_to_xml_api`.
3. Optional diagnostics:
   - `python -m Tafsir.pipeline.analysis.check_divergent_rows [book] [start] [end]`
   - `python -m Tafsir.pipeline.analysis.data_cleaning.rollback_pipeline --book <book>`
4. Serve & browse:
   - `uvicorn Tafsir.pipeline.app:app --reload`

## Useful commands

- Run Gemini API pipeline:
  `python -m Tafsir.pipeline.gemini_api.blocks_to_xml_api --db katheer`
- Run rollback/repair diagnostics pipeline:
  `python -m Tafsir.pipeline.analysis.data_cleaning.rollback_pipeline --book katheer`
- Divergence finder:
  `python -m Tafsir.pipeline.analysis.check_divergent_rows`
- Start API server:
  `uvicorn Tafsir.pipeline.app:app --reload`

## Prerequisites

- Python 3.12+
- Create your own virtual environment in the project root:
  - `python -m venv .venv`
  - `source .venv/bin/activate`
- Install dependencies:
  - `pip install -r requirements.txt`
- GUI automation additionally needs a visible desktop session for pyautogui/OCR.

## Troubleshooting

- Guard skips or retries: inspect `Tafsir/logs/structured_logs_<model>.json` (`guard` and `progress` buckets) and adjust thresholds in `evaluate_guard` if needed.
- API vs GUI: both share guard/normalization; GUI is more brittle (screen/OCR), API is faster/stabler when credentials are available.
