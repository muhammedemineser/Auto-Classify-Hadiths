# Stage 3 — Matching

**Module:** `Tafsir/pipeline/analysis/sahihah/compare_txt_agains_db.py`

Core steps per hadith:
1. Parse number + text + `KUTUBS` list.
2. Normalize + tokenize (text only).
3. Build weighted anchors.
4. Candidate filtering:
   - AND‑phase with strong anchors
   - OR‑phase with top anchors
   - Fallback if still low
5. Order precheck for anchor positions.
6. Multi‑n scoring (`n0`, `n0±1`).
7. Meta penalty for honorific noise.
8. Optional semantic rerank for top‑K.

Output:
- Matches saved per DB with `score`, `hit_rate`, `order_ratio`.
