# Analysis utilities (CLI)

Run modules with `python -m Tafsir.pipeline.analysis.<module> [...]`.

- `compare_tafsir_texts.py <book>`  
  Compares source vs. annotated text token‑by‑token; prints mismatching IDs. Book is logical name (e.g. `katheer`).

- `compare_len_src_ann.py`  
  Builds `text_normalisiert` in the source table (if missing) and lists, for every source row, the annotated row with the smallest normalized length delta. No args.

- `check_divergent_rows.py [book] [start] [end]`  
  Flags rows whose guard metrics are below thresholds. Start/end are optional ID bounds.

Data‑cleaning helpers live in `analysis/data_cleaning/` (see that README for details).***
