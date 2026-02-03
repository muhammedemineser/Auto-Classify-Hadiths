# Stage 0 — Kutub Pattern Filter

**File:** `Tafsir/pipeline/analysis/sahihah/how_much_include_kutub_sittah.py`

Purpose: detect which Kutub Sittah sources are referenced per line, and store them.

Output format:
```
... <line text> \tKUTUBS=["Bukhari","Muslim",...]
```

Notes:
- `KUTUBS` list is JSON and is removed before tokenization in matching.
- This list limits which DBs are searched per line.
