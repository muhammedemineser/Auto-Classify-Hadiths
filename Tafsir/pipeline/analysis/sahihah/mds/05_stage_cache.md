# Stage 2 — Cache Build

**Module:** `Tafsir/pipeline/analysis/sahihah/match_cache.py`

Purpose: convert SQLite → Parquet once per DB.

Cache schema per DB:
- `hadith_number` (float or NaN)
- `hadith_number_raw` (str)
- `arabic_matn` (str)
- `matn_norm` (str)
- `token_count` (int)

Cache location:
- `/app/tools/sahihah/cache/<dbname>.parquet`
