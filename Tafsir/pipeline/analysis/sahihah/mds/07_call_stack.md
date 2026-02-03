# Call Stack (High Level)

1. `main()`
   - Load lines
   - Filter DBs
   - Build cache
   - Optimize params
   - Match all lines
   - Write results DB

2. `match_one_hadith_all()`
   - `parse_hadith_line()`
   - `tokenize_words_from_text()`
   - `select_anchors()`
   - `fetch_candidates_parquet()`
   - `score_candidate_multi_n()`
   - Optional semantic rerank
