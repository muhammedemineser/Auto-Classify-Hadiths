# Sahihah Matching Pipeline

## Candidate Pipeline Flag
- `CANDIDATE_PIPELINE=bm25` uses BM25 candidate generation (default).
- `CANDIDATE_PIPELINE=legacy` uses the legacy anchor/SQL-like candidate pipeline.

Tunable parameters:
- `CANDIDATE_TOPK` (default `200`)
- `CANDIDATE_MIN_TOPK` (default `MIN_CANDS`)
- `BM25_K1`, `BM25_B`

## Build Gold Sample (strict 1:1)
```bash
CACHE_DIR=/tmp/sahihah_cache \
DB_GLOB="/app/tools/ML/Data/normalized_hadith/*.db" \
EVAL_SAMPLE_SIZE=30 \
python tools/tuning/build_gold_sample.py
```

Output:
- `CACHE_DIR/gold/gold_sample.jsonl`

## Run Gold Sample
```bash
CACHE_DIR=/tmp/sahihah_cache \
CANDIDATE_PIPELINE=bm25 \
python tools/tuning/run_gold_sample.py
```

Output:
- `CACHE_DIR/gold/report.json`

## Tests
```bash
CACHE_DIR=/tmp/sahihah_cache \
DB_GLOB="/app/tools/ML/Data/normalized_hadith/Bukhari.db" \
pytest -q
```
