# Stage 1 — Hadith Extraction

**File:** `Tafsir/pipeline/analysis/sahihah/extract_sahihah.py`

Purpose: extract the hadith text from lines and preserve the `KUTUBS` list.

Rules:
- Numbers < 3000: hadith text inside quotes `"..."`.
- Numbers ≥ 3000: hadith text inside parentheses `( ... )`.

Output:
```
<id>\t<hadith_text>\tKUTUBS=[...]
```
