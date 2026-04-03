# Data-cleaning CLIs (run from repo root)

Invoke with `python -m Tafsir.pipeline.analysis.data_cleaning.<module> [...]`

- `duplicated <book|db_path> [--table tafsir_analysis_book]`
  Lists IDs that appear more than once.

Tip: logical book names auto-resolve to `Tafsir/tafsir_books_annotated/<book>_annotated.sqlite3` and `tafsir_analysis_<book>` unless you pass an explicit DB path and `--table`.

## rollback_pipeline

`python -m Tafsir.pipeline.analysis.data_cleaning.rollback_pipeline [--book katheer] [--ids 10 11] [--jsonl Tafsir/logs/fine_diff.jsonl]`

- Default run: executes checks (ID gaps, duplicates, ID=NULL, divergence, fine classification), writes classifications to `Tafsir/logs/fine_diff.jsonl` and event log to `Tafsir/logs/rollback_pipeline.log` (JSONL).
- `--ids`: skips global checks; classifies and processes only the provided IDs.
- `--jsonl`: skips checks; loads classifications directly from the given JSONL and processes them (divergent -> regeneration, medium -> diagnosis+regeneration, minor -> alignment).
- Categories are marked as `[CATEGORY=MINOR|MEDIUM|DIVERGENT]` in Gemini prompts; semantic guidance is defined in `PROMPT_GUIDANCE` in code.
