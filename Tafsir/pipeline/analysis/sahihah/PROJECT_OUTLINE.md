# Sahihah Pipeline — Outline & Overview

**Last updated:** 2026-02-04

**Purpose**
- Match Sahihah Hadith text lines against normalized hadith DBs (Kutub Sittah) with strict, domain-aware scoring.
- Keep candidate generation fast and recall‑first, then apply existing n‑gram/order‑ratio scoring unchanged.

**High-Level Data Flow**
1. **Input parsing**: Read `sahihah_hadith_extracted_in_sittah.txt` and parse `hadith_id`, text, and optional `KUTUBS` list.
2. **Normalization + tokenization**: `normalize()` + `tokenize_words_from_text()` create canonical token lists.
3. **Candidate generation**:
   - **BM25 (default)**: `rank-bm25` over `tokens_norm` from Parquet cache, Top‑K candidates.
   - **Legacy**: anchor‑based substring scan over `matn_norm` in Parquet, optional fallback.
4. **Scoring (unchanged)**: multi‑n‑gram overlap + order ratio (`score_candidate_multi_n_from_precomputed`).
5. **Optional semantic rerank**: HF sentence transformer for top‑K only (`match_semantic`).
6. **Output**: write matches to `in_sittah_matches.db` and params to `best_ngram_params.json`.

**Core Modules (What they do)**
- `compare_txt_agains_db.py`
  - Main pipeline driver, param search, batching, multiprocessing.
  - Implements `match_one_hadith_all()` and candidate flow selection.
  - All scoring logic lives here and is intentionally unchanged.
- `match_cache.py`
  - Builds Parquet cache from DBs and provides fast column access.
  - Stores `tokens_norm` and `ngrams_*` columns for scoring.
  - Supports direct row fetch by index for BM25 candidates.
- `match_ir.py`
  - BM25 index build and top‑K retrieval over `tokens_norm`.
  - In‑memory index (no persistence yet).
- `match_logging.py`
  - Debug logging for anchors, candidate flow, coverage, and cache stats.
- `match_semantic.py`
  - Optional semantic reranker with cache (`semantic_cache.db`).
- `match_stanza.py`
  - Optional POS tagging to weight anchors (`stanza_cache.db`).

**Inputs**
- Text sources:
  - `sahihah_komplett.txt`
  - `sahihah_hadith_extracted_in_sittah.txt`
  - `in_sittah.txt`
- DBs:
  - `/app/tools/ML/Data/normalized_hadith/*.db`

**Outputs**
- Results DB:
  - `/app/tools/fetch_ketab/sahihah/in_sittah_matches.db`
- Params JSON:
  - `/app/tools/sahihah/best_ngram_params.json`
- Parquet cache:
  - `/app/tools/sahihah/cache/*.parquet`

**Tools & Tests**
- `tools/tuning/build_gold_sample.py`
  - Builds strict 1:1 gold sample with exact normalized matches.
  - Verifies Rank‑1 by default using the current pipeline.
- `tools/tuning/run_gold_sample.py`
  - Runs gold sample through pipeline and writes `report.json`.
  - Captures p50/p95 timings, candidate counts, fallback rate, process snapshot.
- `tests/test_gold_sample.py`
  - Gold sample builds, runs fast, and Rank‑1 matches.

**Key Flags (Operational)**
- `CANDIDATE_PIPELINE=bm25|legacy` (default `bm25`)
- `CANDIDATE_TOPK` (default `200`)
- `CANDIDATE_MIN_TOPK` (default `MIN_CANDS`)
- `BM25_K1`, `BM25_B`
- `CACHE_DIR` (default `/app/tools/sahihah/cache`)
- `DB_GLOB` (default `/app/tools/ML/Data/normalized_hadith/*.db`)
- `MAX_WORKERS` (set to `1` for small‑sample profiling)
- `ENABLE_STANZA`, `ENABLE_SEM_RERANK`

---

## Individuale Einschätzung der aktuellen Situation (inkl. Inkonsistenzen)

**Beobachtung (Live‑Check in diesem Workspace)**
- Im Cache‑Verzeichnis `/app/tools/sahihah/cache` liegen Parquet‑Dateien für alle DBs.
- Diese Parquet‑Dateien enthalten **keine** `ngrams_*`‑Spalten (max_ngram=0), obwohl die aktuelle Pipeline `ngrams_1..23` erwartet.
- Parquet‑Row‑Counts sind durchgehend etwas kleiner als die DB‑Row‑Counts. Das ist plausibel, weil `_build_parquet_table()` Rows mit `arabic_matn IS NULL` überspringt.

**Aktueller Cache‑Status (Snapshot)**
| DB | DB Rows | Parquet Rows | Max Ngram Col | Parquet Size (bytes) |
| --- | --- | --- | --- | --- |
| AbuDaud.db | 5145 | 5028 | 0 | 68482981 |
| Bukhari.db | 7443 | 7439 | 0 | 3655647 |
| IbnMajah.db | 4402 | 4386 | 0 | 1314715 |
| Muslim.db | 7333 | 6806 | 0 | 2602646 |
| Nesai.db | 5716 | 5633 | 0 | 1711869 |
| Tirmizi.db | 4368 | 4278 | 0 | 1988934 |

**Interpretation**
- Die Parquet‑Caches sind **inkonsistent** mit dem aktuellen Codepfad, der `ngrams_*` erwartet.
- Wahrscheinlich wurden diese Parquets mit `max_ngram_n=0` oder älterem Code erzeugt, oder der Run wurde vor dem Rebuild abgebrochen.
- Konsequenz: Kandidaten‑Scoring kann in der Hauptpipeline fehlschlagen oder suboptimal laufen, wenn diese Caches verwendet werden.

**Empfohlener Reset/Recovery (sauber, reproduzierbar)**
1. **Sauberes Cache‑Ziel wählen** (empfohlen):
   - `CACHE_DIR=/tmp/sahihah_cache` für Tests und Iteration.
2. **Rebuild erzwingen**:
   - Entweder alte Parquets löschen **oder** neuen `CACHE_DIR` nutzen.
   - `compare_txt_agains_db.py` baut den Cache mit `max_ngram_n` aus den aktuellen Parametern.
3. **Integritätscheck**:
   - Prüfen, ob `ngrams_1..max` in Parquet enthalten sind.
   - DB‑Row‑Counts vs Parquet‑Row‑Counts vergleichen (leichte Abweichung ist ok, große nicht).

**Minimaler Verifikations‑Loop (schnell, deterministisch)**
- Gold Sample bauen:
  - `CACHE_DIR=/tmp/sahihah_cache DB_GLOB="/app/tools/ML/Data/normalized_hadith/Bukhari.db" EVAL_SAMPLE_SIZE=30 python tools/tuning/build_gold_sample.py`
- Sample laufen lassen:
  - `CACHE_DIR=/tmp/sahihah_cache CANDIDATE_PIPELINE=bm25 MAX_WORKERS=1 DEBUG=0 python tools/tuning/run_gold_sample.py`
- Report prüfen:
  - `CACHE_DIR/gold/report.json`

**Risiken, wenn nichts getan wird**
- Fehlende `ngrams_*`‑Spalten erzeugen inkonsistente Scoring‑Inputs.
- Abgebrochene Runs können halb‑gültige Caches hinterlassen, die „funktionieren“, aber nicht kompatibel sind.

---

## Wo was liegt (Kurzreferenz)
- **Pipeline & Matching**: `compare_txt_agains_db.py`
- **Parquet Cache**: `match_cache.py`
- **BM25 Candidate Gen**: `match_ir.py`
- **Stanza POS Cache**: `match_stanza.py` (`stanza_cache.db`)
- **Semantic Cache**: `match_semantic.py` (`semantic_cache.db`)
- **Gold Sample Tools**: `tools/tuning/`
- **Docs (legacy)**: `mds/*.md`
