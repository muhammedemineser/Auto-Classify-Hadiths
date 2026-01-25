# Data-cleaning CLIs (run from repo root)

Invoke with `python -m Tafsir.pipeline.analysis.data_cleaning.<module> [...]`

- `reconcile_mismatches --db katheer [--ids "1,2,3"]`  
  Relinks annotated IDs to best source match. `--ids` restricts to specific annotated IDs; otherwise all.

- `reconcile_only_id_null --db katheer`  
  Fills missing IDs by best match (only rows with NULL id).

- `duplicated <book|db_path> [--table tafsir_analysis_book]`  
  Lists IDs that appear more than once.

- `backfill_normalized <book|db_path> [--table ...]`  
  Normalizes `extracted_text_full` into `extracted_text_normalized` where empty.

- `rebuild_derived_columns --db katheer`  
  Re-extracts all tag columns from `extracted_text_full` for every row.

- `insert_hard_coded/replace_many_mismatch.py`  
  Manual repair helper; edit constants inside before running.

Tip: logical book names auto-resolve to `Tafsir/tafsir_books_annotated/<book>_annotated.sqlite3` and `tafsir_analysis_<book>` unless you pass an explicit DB path and `--table`.***

## rollback_pipeline

`python -m Tafsir.pipeline.analysis.data_cleaning.rollback_pipeline [--book katheer] [--ids 10 11] [--jsonl Tafsir/logs/fine_diff.jsonl]`

- Default run: führt alle Checks (ID-Lücken, Duplikate, NULL-Felder, Divergenzen, Feinklassifizierung), schreibt Klassifizierungen in `logs/fine_diff.jsonl` und Event-Log `logs/rollback_pipeline.log` (JSONL).
- `--ids`: überspringt globale Checks; klassifiziert und verarbeitet nur die angegebenen IDs.
- `--jsonl`: überspringt Checks; lädt Klassifizierungen direkt aus der angegebenen JSONL und verarbeitet sie (divergent → Regeneration, medium → Diagnose+Regeneration, minor → Alignment).
- Kategorien werden mit `[CATEGORY=MINOR|MEDIUM|DIVERGENT]` in den Gemini-Prompts markiert; die menschliche Bedeutung liegt in `PROMPT_GUIDANCE` im Code.
