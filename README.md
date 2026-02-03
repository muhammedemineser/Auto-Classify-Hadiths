# classify (Tafsir pipeline) – branch overview

This branch contains a lightweight pipeline that turns raw Tafsir texts (Arabic exegesis) stored in SQLite into consistently tagged XML using Google’s Gemini (GUI automation or API), then reconciles and serves the annotated corpus via a small FastAPI app.

## Repository layout

- `run_active_as_module.py` – helper to run the package as a module from anywhere.
- `Tafsir/config` – path & default settings (`BOOKS_DIR`, `ANNOTATED_DIR`, `DEFAULT_TAFSIR`).
- `Tafsir/pipeline/app.py` – FastAPI server that renders/searches the annotated Tafsir; auto-discovers source/annotated DBs.
- `Tafsir/pipeline/gemini_gui` – browser automation flow (pyautogui + OCR) to drive Gemini UI; core logic in `blocks_to_xml_gui.py`; prompt text in `gui_app_prompt.txt`.
- `Tafsir/pipeline/gemini_api` – API-based runner with the same guard/cleanup logic (`blocks_to_xml_api.py`).
- `Tafsir/pipeline/analysis` – CLI utilities for inspection; `analysis/data_cleaning` holds reconciliation/rollback helpers (see their README files).
- `Tafsir/pipeline/static` – HTML/XML viewer assets the FastAPI app serves.
- `Tafsir/tafsir_books` – source SQLite DBs (each table named after the book, containing `id, text`).
- `Tafsir/tafsir_books_annotated` – generated annotated DBs (`<book>_annotated.sqlite3`) with section/block/chunk tables.
- `Tafsir/utils` – thin aliases (e.g., `blocks_to_xml_api.py` imports the GUI implementation to keep monkeypatches in sync).
- `Tafsir/logs` and `Tafsir/pipeline/analysis/data_cleaning_out` – guard/progress/diagnostic logs written by the automation scripts.

## Data model

- Source DB table: `<book>` with `id, text`.
- Annotated DB tables:
  - `tafsir_analysis_<book>`: `id`, XML in `extracted_text_full`, normalized text in `extracted_text_normalized`, timestamps.
  - `tafsir_analysis_<book>_blocks` / `_chunks`: block/chunk breakdown with FK back to sections.
    Guard logic (`evaluate_guard`) checks token coverage, n‑gram overlap, and length ratio to keep bad generations out.

## Typical pipeline

1. Place a raw source DB in `Tafsir/tafsir_books/<book>.sqlite3` (table name `<book>`).
2. Generate annotations
   - GUI route: run the browser automation in `Tafsir/pipeline/gemini_gui/blocks_to_xml_gui.py` (drives Gemini UI).
   - GUI Configuration: Coordinates may require adjustment on different devices; use mouse.py to calibrate the $x$ and $y$ values for each step.
   - API route: `python -m Tafsir.pipeline.gemini_api.blocks_to_xml_api` (calls Gemini API). Both use the same guard/thresholds.
3. Clean/reconcile:
   - `python -m Tafsir.pipeline.analysis.data_cleaning.reconcile_mismatches --db <book> [--ids 1,2,3]` realigns IDs by best text match.
   - `python -m Tafsir.pipeline.analysis.data_cleaning.reconcile_only_id_null --db <book>` fixes NULL IDs by best match.
   - `python -m Tafsir.pipeline.analysis.data_cleaning.backfill_normalized <book>` populates missing `extracted_text_normalized`.
   - `python -m Tafsir.pipeline.analysis.data_cleaning.rebuild_derived_columns --db <book>` re-extracts tag columns from XML.
   - `python -m Tafsir.pipeline.analysis.data_cleaning.rollback_pipeline --book <book>` collects anomalies (gaps, duplicates, divergence) and triggers Gemini regeneration/diagnostics.
   - `python -m Tafsir.pipeline.analysis.compare_len_src_ann` computes minimal length deltas and flags odd pairs.
4. Serve & browse: `uvicorn Tafsir.pipeline.app:app --reload` (or run under a process manager).

## Useful commands

- Reconcile (best-match relinking):  
  `python -m Tafsir.pipeline.analysis.data_cleaning.reconcile_mismatches --db katheer`
- Fix NULL ids only:  
  `python -m Tafsir.pipeline.analysis.data_cleaning.reconcile_only_id_null --db katheer`
- Backfill normalized text:  
  `python -m Tafsir.pipeline.analysis.data_cleaning.backfill_normalized katheer`
- Rebuild derived tag columns from XML:  
  `python -m Tafsir.pipeline.analysis.data_cleaning.rebuild_derived_columns --db katheer`
- Run rollback pipeline (collect anomalies + regenerate via Gemini):  
  `python -m Tafsir.pipeline.analysis.data_cleaning.rollback_pipeline --book katheer`
- Length-based sanity check:  
  `python -m Tafsir.pipeline.analysis.compare_len_src_ann`
- Divergence finder:  
  `python -m Tafsir.pipeline.analysis.check_divergent_rows`
- Start API server:  
  `uvicorn Tafsir.pipeline.app:app --reload`

## Notes & conventions

- Default book is `katheer`; override via env `DEFAULT_TAFSIR` or CLI options where provided.
- IDs are kept identical between source and annotated tables; reconciliation updates IDs while preventing collisions.
- `logs/guard.log` and `logs/progress.log` capture guard decisions and Gemini interactions; check them first when something looks off.

## Prerequisites

- Python 3.12+ (a `.venv` is already used in this workspace).
- Install deps (example): `pip install -r requirements.txt` (or `pipenv install` if you use the provided Pipfile). GUI automation additionally needs a visible desktop session for pyautogui/OCR.

## Troubleshooting

- Mismatched lengths or wrong IDs: run `reconcile_mismatches` and inspect `compare_len_src_ann` output.
- Guard skips: look at `logs/guard.log`; adjust thresholds in `evaluate_guard` if needed.
- API vs GUI: both share guard/normalization; GUI is more brittle (screen/OCR), API is faster/stabler when credentials are available.
