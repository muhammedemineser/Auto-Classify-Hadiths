# Inputs & Outputs

## Inputs
- Source: `sahihah_komplett.txt`
- In‑Sittah lines: `in_sittah.txt`
- Extracted hadiths: `sahihah_hadith_extracted_in_sittah.txt`
- DBs: `/app/tools/ML/Data/normalized_hadith/*.db`

## Outputs
- Cache: `/app/tools/sahihah/cache/*.parquet`
- Results DB: `/app/tools/fetch_ketab/sahihah/in_sittah_matches.db`
- Best params: `/app/tools/sahihah/best_ngram_params.json`
