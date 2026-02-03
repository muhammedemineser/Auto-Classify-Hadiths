You are Codex. Implement a new, self-contained “student model” training + inference subsystem in a separate directory inside this repo. Do NOT modify existing Tafsir pipeline code except to add optional CLI entrypoints or documentation if needed. The new subsystem must:

- Read INPUT training data from: Tafsir/tafsir_books/{book}.sqlite3
- Read TARGET/OUTPUT training data (solutions) from: Tafsir/tafsir_books_annotated/{book}\_annotated.sqlite3
- Produce a trainable dataset that maps raw tafsir text → structured semantic XML tags (or a robust intermediate JSON AST that deterministically renders to XML).
- Provide training, evaluation, and inference CLIs.
- Guarantee syntactic correctness (XML well-formed + schema constraints), preservation checks, and allow fallback to teacher (Gemini) later (but do NOT implement Gemini calls here).

Repository constraints:

- Python 3.12
- Must run locally inside this repo’s venv.
- Keep all new work under a new folder, e.g. tools/tafsir_student/ (or similar). No global refactors.
- Add minimal dependencies; prefer standard library + widely used packages. If you add deps, pin them in a requirements.txt inside the new folder.

====================================================================

1. # Create new directory structure
   Create: tools/tafsir_student/

With the following layout (exact):
tools/tafsir_student/
README.md
requirements.txt
pyproject.toml (optional, but preferred; if present, configure as a package)
tafsir_student/
**init**.py
config.py
db/
**init**.py
sqlite.py
schemas.py
data/
**init**.py
extract.py
align.py
build_jsonl.py
split.py
xml/
**init**.py
normalize.py
validate.py
render.py
ast.py
model/
**init**.py
baseline.py
tokenization.py
train.py
eval.py
infer.py
metrics.py
cli/
**init**.py
main.py
tests/
**init**.py
test_extract.py
test_align.py
test_validate.py
test_render_roundtrip.py

All code must be type-annotated and runnable. Provide docstrings and clear error messages. Provide sane defaults. All paths must be relative to repo root when invoked from repo root.

# ==================================================================== 2) Understand existing DB structure (must be discovered programmatically)

Do NOT hardcode table/column names except generic fallbacks. Implement schema discovery by inspecting SQLite.

INPUT DB: Tafsir/tafsir_books/{book}.sqlite3

- Expect at least one table. Commonly the table name == {book}.
- Expect at least columns like id, text_normalisiert.

TARGET DB: Tafsir/tafsir_books_annotated/{book}\_annotated.sqlite3

- Contains derived tables (sections/blocks/chunks/etc). Must be discovered.
- Goal: reconstruct a canonical XML for each source id (or for each unit that can be aligned reliably).
- Implement: discover where the annotated XML lives and candidate columns.
- If annotated DB is structured across multiple tables (chunks/blocks), implement join logic to assemble a per-source-id XML in canonical form.
- If cannot reconstruct perfectly, implement a “best-effort” assembler and mark sample status.

Deliverable:

- A robust “alignment” layer that yields training pairs:
  (source_id, source_text, target_xml_canonical)

# ==================================================================== 3) Canonical target representation (use intermediate AST + deterministic XML renderer)

Implement a two-stage output to maximize robustness:

Stage A: model outputs JSON AST (strict schema)
Stage B: deterministic renderer converts AST → canonical XML

Define AST schema in tafsir_student/xml/ast.py:

Top-level:
{
"sections": [
{
"blocks": [
{
"chunks": [
{
"items": [
{"tag": "quran_verse", "text": "..."},
{"tag": "linguistic_analysis", "text": "..."},
...
]
}
]
}
]
}
]
}

Rules:

- Allowed tags MUST be configurable (list). Default allowed tags derived by scanning the annotated DB for tag names.
- Unknown tags must be rejected by validator.
- Text nodes must be strings; whitespace preserved as-is but renderer must canonicalize indentation/spacing.

Renderer requirements (tafsir_student/xml/render.py):

- Output root: <tafsir_section> ... </tafsir_section> as in our existing example.
- Enforce stable ordering: sections→blocks→chunks→items.
- Canonical formatting: no trailing spaces; normalize newlines to \n; optionally pretty-print with 2-space indent (configurable).
- Escape XML special chars properly.

Validator requirements (tafsir_student/xml/validate.py):

- Validate well-formed XML.
- Validate tagset: only allowed tags and the structural wrapper tags (tafsir_section, tafsir_section_block, tafsir_chunk).
- Validate preservation: normalized_plaintext(source_text) must be “mostly contained” in normalized_plaintext(rendered_xml) OR vice versa within a threshold. Implement config threshold and report metrics.
- Provide a function validate_pair(source_text, xml) that returns a structured report.

Normalization (tafsir_student/xml/normalize.py):

- Use the existing normalize function for Arabic normalization:

# ==================================================================== 4) Data extraction & alignment

Implement:

- tafsir_student/data/extract.py
  - load_source_rows(book, repo_root) -> List[SourceRow(id:int|str, text:str)]
  - discover text column; keep original id type.

- tafsir_student/data/align.py
  - load_annotated_targets(book) -> mapping id -> target_xml
  - Implement multiple strategies:
    Strategy 1: direct id match if annotated tables have source_id/id.
    Strategy 2: if annotated stores original text alongside xml, match by normalized text similarity.
  - Return: List[AlignedSample] with status:
    - "aligned_exact"
    - "missing_target"
    - "invalid_target"
  - Provide detailed logs for why alignment failed.

- tafsir_student/data/build_jsonl.py
  - Build dataset JSONL for training:
    Each line: {"book":..., "id":..., "input_text":..., "target_ast":..., "target_xml":..., "status":..., "tags":...}
  - Convert target_xml → target_ast via a parser (see below) to get training label.
  - If XML→AST parse fails, keep xml but mark status and optionally skip.

XML→AST parser (tafsir_student/xml/ast.py or xml/validate.py):

- Parse canonical annotated XML into AST:
  - Recognize wrappers: tafsir_section, tafsir_section_block, tafsir_chunk
  - For each chunk, collect child elements in order: each child tag + inner text.
  - Mixed text nodes: preserve as plain text items with tag "**text**" OR fold into adjacent items. Decide one approach and implement consistently.
  - Default: represent raw text segments as {"tag":"**text**", "text":"..."} and allow renderer to emit them as plain text nodes (no wrapping tag) OR wrap them in <text> if you prefer; but this must be stable and documented.
- Include config to either keep "**text**" or drop it.

If you choose not to support raw text nodes, then you MUST ensure target XML is representable and provide a fallback transformation (e.g. wrap stray text in <plain_text>).

######################################################################################
Erweitere diesen Schritt hier
[5) Baseline model first (no heavy ML dependency required)

Before implementing NN training, provide a baseline that is already useful and sets up the pipeline:

Baseline in tafsir_student/model/baseline.py:

- Rule-based tagger using:
  - Regex/heuristics to detect Quran verses in parentheses, hadith markers, isnad markers, source references as you find them in tools/ML/RX
  - Map heuristic matches to tags from allowed tag list.
- Output AST.

This baseline enables:

- End-to-end data flow
- Validation metrics
- A reference point]

durch die maximale ausschöpfung des nutzens der daraus entsteht, hadithe, isnad und quran als saubere daten in dbs zu haben und daran die wahrscheinlichkeit auf einen treffer ausmachen zu können. Folgendes Datenbank Schema liegt vor:

[Data to identify Quran verses:

Quran:
Database: quran.db

Table: ayah_metadata_new

- id: INTEGER [PK]
- sura_number: INTEGER
- ayah_number: INTEGER
- ayah_text: TEXT
  -> FK: ['sura_number'] -> sura.['sura_number']

Table: sura

- sura_number: INTEGER [PK]
- sura_name: VARCHAR(100)

Data to identify Hadith:

Hadith:
Database: Bukhari.db

Table: chapters

- Chapter_Number: TEXT
- Chapter_English: TEXT
- Chapter_Arabic: TEXT
- chapter_id: INTEGER

Table: hadiths

- Chapter_Number: TEXT
- Section_Number: TEXT
- Hadith_number: TEXT
- English_Hadith: TEXT
- English_Isnad: TEXT
- English_Matn: TEXT
- Arabic_Hadith: TEXT
- Arabic_Isnad: TEXT
- Arabic_Matn: TEXT
- Arabic_Comment: TEXT
- English_Grade: TEXT
- Arabic_Grade: TEXT
- section_id: INTEGER
- hadith_id: INTEGER

Table: sections

- Chapter_Number: TEXT
- Section_Number: TEXT
- Section_English: TEXT
- Section_Arabic: TEXT
- chapter_id: INTEGER
- section_id: INTEGER

Database: Muslim.db

Table: chapters

- Chapter_Number: TEXT
- Chapter_English: TEXT
- Chapter_Arabic: TEXT
- chapter_id: INTEGER

Table: hadiths

- Chapter_Number: TEXT
- Section_Number: TEXT
- Hadith_number: TEXT
- English_Hadith: TEXT
- English_Isnad: TEXT
- English_Matn: TEXT
- Arabic_Hadith: TEXT
- Arabic_Isnad: TEXT
- Arabic_Matn: TEXT
- Arabic_Comment: TEXT
- English_Grade: TEXT
- Arabic_Grade: TEXT
- section_id: INTEGER
- hadith_id: INTEGER

Table: sections

- Chapter_Number: TEXT
- Section_Number: TEXT
- Section_English: TEXT
- Section_Arabic: TEXT
- chapter_id: INTEGER
- section_id: INTEGER

Database: AbuDaud.db

Table: chapters

- Chapter_Number: TEXT
- Chapter_English: TEXT
- Chapter_Arabic: TEXT
- chapter_id: INTEGER

Table: hadiths

- Chapter_Number: TEXT
- Section_Number: TEXT
- Hadith_number: TEXT
- English_Hadith: TEXT
- English_Isnad: TEXT
- English_Matn: TEXT
- Arabic_Hadith: TEXT
- Arabic_Isnad: TEXT
- Arabic_Matn: TEXT
- Arabic_Comment: TEXT
- English_Grade: TEXT
- Arabic_Grade: TEXT
- section_id: INTEGER
- hadith_id: INTEGER

Table: sections

- Chapter_Number: TEXT
- Section_Number: TEXT
- Section_English: TEXT
- Section_Arabic: TEXT
- chapter_id: INTEGER
- section_id: INTEGER

Database: Tirmizi.db

Table: chapters

- Chapter_Number: TEXT
- Chapter_English: TEXT
- Chapter_Arabic: TEXT
- chapter_id: INTEGER

Table: hadiths

- Chapter_Number: TEXT
- Section_Number: TEXT
- Hadith_number: TEXT
- English_Hadith: TEXT
- English_Isnad: TEXT
- English_Matn: TEXT
- Arabic_Hadith: TEXT
- Arabic_Isnad: TEXT
- Arabic_Matn: TEXT
- Arabic_Comment: TEXT
- English_Grade: TEXT
- Arabic_Grade: TEXT
- section_id: INTEGER
- hadith_id: INTEGER

Table: sections

- Chapter_Number: TEXT
- Section_Number: TEXT
- Section_English: TEXT
- Section_Arabic: TEXT
- chapter_id: INTEGER
- section_id: INTEGER

Database: Nesai.db

Table: chapters

- Chapter_Number: TEXT
- Chapter_English: TEXT
- Chapter_Arabic: TEXT
- chapter_id: INTEGER

Table: hadiths

- Chapter_Number: TEXT
- Section_Number: TEXT
- Hadith_number: TEXT
- English_Hadith: TEXT
- English_Isnad: TEXT
- English_Matn: TEXT
- Arabic_Hadith: TEXT
- Arabic_Isnad: TEXT
- Arabic_Matn: TEXT
- Arabic_Comment: TEXT
- English_Grade: TEXT
- Arabic_Grade: TEXT
- section_id: INTEGER
- hadith_id: INTEGER

Table: sections

- Chapter_Number: TEXT
- Section_Number: TEXT
- Section_English: TEXT
- Section_Arabic: TEXT
- chapter_id: INTEGER
- section_id: INTEGER

Database: IbnMajah.db

Table: chapters

- Chapter_Number: TEXT
- Chapter_English: TEXT
- Chapter_Arabic: TEXT
- chapter_id: INTEGER

Table: hadiths

- Chapter_Number: TEXT
- Section_Number: TEXT
- Hadith_number: TEXT
- English_Hadith: TEXT
- English_Isnad: TEXT
- English_Matn: TEXT
- Arabic_Hadith: TEXT
- Arabic_Isnad: TEXT
- Arabic_Matn: TEXT
- Arabic_Comment: TEXT
- English_Grade: TEXT
- Arabic_Grade: TEXT
- section_id: INTEGER
- hadith_id: INTEGER

Table: sections

- Chapter_Number: TEXT
- Section_Number: TEXT
- Section_English: TEXT
- Section_Arabic: TEXT
- chapter_id: INTEGER
- section_id: INTEGER
  ]
  Ausserdem haben wir folgende Regex module erstellt. Konkretisiere den Prompt um die Anwendung dieser Module und ihre Rolle zu verdeutlichen.
  ##################################################################################################################

# ====================================================================

5. Baseline model first (no heavy ML dependency required)

Before implementing NN training, provide a baseline that is already useful and sets up the pipeline:

Baseline in tafsir_student/model/baseline.py:

- Rule-based tagger using:
  - Regex/heuristics to detect Quran verses in parentheses, hadith markers, isnad markers, source references as you find them in tools/ML/RX
  - Map heuristic matches to tags from allowed tag list.
- Output AST.

This baseline enables:

- End-to-end data flow
- Validation metrics
- A reference point

Data to identify Quran verses:

Quran:
Database: quran.db

Table: ayah_metadata_new

- id: INTEGER [PK]
- sura_number: INTEGER
- ayah_number: INTEGER
- ayah_text: TEXT
  -> FK: ['sura_number'] -> sura.['sura_number']

Table: sura

- sura_number: INTEGER [PK]
- sura_name: VARCHAR(100)

Data to identify Hadith:

Hadith:
Database: Bukhari.db

Table: chapters

- Chapter_Number: TEXT
- Chapter_English: TEXT
- Chapter_Arabic: TEXT
- chapter_id: INTEGER

Table: hadiths

- Chapter_Number: TEXT
- Section_Number: TEXT
- Hadith_number: TEXT
- English_Hadith: TEXT
- English_Isnad: TEXT
- English_Matn: TEXT
- Arabic_Hadith: TEXT
- Arabic_Isnad: TEXT
- Arabic_Matn: TEXT
- Arabic_Comment: TEXT
- English_Grade: TEXT
- Arabic_Grade: TEXT
- section_id: INTEGER
- hadith_id: INTEGER

Table: sections

- Chapter_Number: TEXT
- Section_Number: TEXT
- Section_English: TEXT
- Section_Arabic: TEXT
- chapter_id: INTEGER
- section_id: INTEGER

Database: Muslim.db

Table: chapters

- Chapter_Number: TEXT
- Chapter_English: TEXT
- Chapter_Arabic: TEXT
- chapter_id: INTEGER

Table: hadiths

- Chapter_Number: TEXT
- Section_Number: TEXT
- Hadith_number: TEXT
- English_Hadith: TEXT
- English_Isnad: TEXT
- English_Matn: TEXT
- Arabic_Hadith: TEXT
- Arabic_Isnad: TEXT
- Arabic_Matn: TEXT
- Arabic_Comment: TEXT
- English_Grade: TEXT
- Arabic_Grade: TEXT
- section_id: INTEGER
- hadith_id: INTEGER

Table: sections

- Chapter_Number: TEXT
- Section_Number: TEXT
- Section_English: TEXT
- Section_Arabic: TEXT
- chapter_id: INTEGER
- section_id: INTEGER

Database: AbuDaud.db

Table: chapters

- Chapter_Number: TEXT
- Chapter_English: TEXT
- Chapter_Arabic: TEXT
- chapter_id: INTEGER

Table: hadiths

- Chapter_Number: TEXT
- Section_Number: TEXT
- Hadith_number: TEXT
- English_Hadith: TEXT
- English_Isnad: TEXT
- English_Matn: TEXT
- Arabic_Hadith: TEXT
- Arabic_Isnad: TEXT
- Arabic_Matn: TEXT
- Arabic_Comment: TEXT
- English_Grade: TEXT
- Arabic_Grade: TEXT
- section_id: INTEGER
- hadith_id: INTEGER

Table: sections

- Chapter_Number: TEXT
- Section_Number: TEXT
- Section_English: TEXT
- Section_Arabic: TEXT
- chapter_id: INTEGER
- section_id: INTEGER

Database: Tirmizi.db

Table: chapters

- Chapter_Number: TEXT
- Chapter_English: TEXT
- Chapter_Arabic: TEXT
- chapter_id: INTEGER

Table: hadiths

- Chapter_Number: TEXT
- Section_Number: TEXT
- Hadith_number: TEXT
- English_Hadith: TEXT
- English_Isnad: TEXT
- English_Matn: TEXT
- Arabic_Hadith: TEXT
- Arabic_Isnad: TEXT
- Arabic_Matn: TEXT
- Arabic_Comment: TEXT
- English_Grade: TEXT
- Arabic_Grade: TEXT
- section_id: INTEGER
- hadith_id: INTEGER

Table: sections

- Chapter_Number: TEXT
- Section_Number: TEXT
- Section_English: TEXT
- Section_Arabic: TEXT
- chapter_id: INTEGER
- section_id: INTEGER

Database: Nesai.db

Table: chapters

- Chapter_Number: TEXT
- Chapter_English: TEXT
- Chapter_Arabic: TEXT
- chapter_id: INTEGER

Table: hadiths

- Chapter_Number: TEXT
- Section_Number: TEXT
- Hadith_number: TEXT
- English_Hadith: TEXT
- English_Isnad: TEXT
- English_Matn: TEXT
- Arabic_Hadith: TEXT
- Arabic_Isnad: TEXT
- Arabic_Matn: TEXT
- Arabic_Comment: TEXT
- English_Grade: TEXT
- Arabic_Grade: TEXT
- section_id: INTEGER
- hadith_id: INTEGER

Table: sections

- Chapter_Number: TEXT
- Section_Number: TEXT
- Section_English: TEXT
- Section_Arabic: TEXT
- chapter_id: INTEGER
- section_id: INTEGER

Database: IbnMajah.db

Table: chapters

- Chapter_Number: TEXT
- Chapter_English: TEXT
- Chapter_Arabic: TEXT
- chapter_id: INTEGER

Table: hadiths

- Chapter_Number: TEXT
- Section_Number: TEXT
- Hadith_number: TEXT
- English_Hadith: TEXT
- English_Isnad: TEXT
- English_Matn: TEXT
- Arabic_Hadith: TEXT
- Arabic_Isnad: TEXT
- Arabic_Matn: TEXT
- Arabic_Comment: TEXT
- English_Grade: TEXT
- Arabic_Grade: TEXT
- section_id: INTEGER
- hadith_id: INTEGER

Table: sections

- Chapter_Number: TEXT
- Section_Number: TEXT
- Section_English: TEXT
- Section_Arabic: TEXT
- chapter_id: INTEGER
- section_id: INTEGER

# ==================================================================== 6) Neural model training (choose a practical approach)

Implement an initial trainable student with a lightweight approach:

Option A (preferred): Sequence-to-sequence fine-tuning with HuggingFace Transformers + LoRA (PEFT)

- Model: small Arabic-capable or multilingual seq2seq model.
- Output format: JSON AST as a string (constrained via JSON schema post-parse).
- Implement:
  - tafsir_student/model/train.py: loads JSONL, splits, fine-tunes with LoRA, saves artifacts.
  - tafsir_student/model/infer.py: loads model, generates AST JSON, validates, renders XML.
  - tafsir_student/model/eval.py: computes metrics described below.
- Add dependencies in requirements.txt: transformers, peft, accelerate, datasets, torch, sentencepiece (if needed).

If dependencies are too heavy for tests, keep unit tests for non-ML parts and provide smoke-only for ML with skip.

Option B: token-classification with spaCy / PyTorch (only if you decide it fits).
Prefer Option A unless strong reason.

Your implementation MUST:

- Enforce post-generation JSON parse. If invalid JSON, attempt a single repair pass: (1) strip trailing junk, (2) re-parse; do not implement an LLM repair.
- Validate tags, then render XML.
- If validation fails, return structured error.

==================================================================== 7) Metrics & evaluation
Implement in tafsir_student/model/metrics.py:

- xml_well_formed_rate
- tagset_compliance_rate
- preservation_score (token overlap under normalize modes)
- ast_tree_similarity (simple: tag-sequence F1; optional: tree edit distance if easy)
- exact_match_rate on canonicalized XML (string compare)

Canonicalize XML for comparison:

- normalize whitespace between tags
- stable indentation
- normalized text with strict mode
- attribute ordering (if any)

Evaluation CLI:

- Load test split
- Run baseline and/or model
- Print summary table + write JSON report

==================================================================== 8) CLI commands
Implement a single entrypoint: python -m tools.tafsir_student.tafsir_student.cli.main (or python -m tafsir_student.cli.main if packaged). Provide console scripts if pyproject is used.

Commands (exact names):

- extract --book katheer
  Prints discovered schema and rowcounts for input+annotated DB.

- build-dataset --book katheer --out tools/tafsir_student/out/katheer.jsonl
  Builds aligned dataset JSONL plus a stats report.

- validate-samples --jsonl PATH --limit N
  Validates target XML and reports failures.

- train --jsonl PATH --model MODEL_NAME --outdir tools/tafsir_student/models/katheer_v1
  Trains student model.

- eval --jsonl PATH --modeldir PATH
  Runs evaluation.

- infer --modeldir PATH --text "..."
  Outputs AST + rendered XML + validation report.

All commands must have --repo-root override and sensible defaults.

==================================================================== 9) Tests
Write unit tests for:

- DB discovery (use temporary sqlite fixtures created in-test; do not depend on large repo DBs).
- XML parse→AST→render roundtrip.
- Tagset validation.
- Preservation normalization.

ML training tests can be skipped by default.

==================================================================== 10) Documentation
tools/tafsir_student/README.md must include:

- What it does
- How it discovers DB tables
- How alignment works (strategies, failure modes)
- How to build dataset, validate, train, eval, infer
- How tags are discovered from annotated DB
- How to integrate later into pipeline (student-first, teacher-fallback) conceptually (no code in existing pipeline now)

==================================================================== 11) Non-negotiable behaviors

- Never crash without actionable message. Surface which DB/table/column caused failure.
- Every data sample carries status + validation report.
- Output directory created only when explicitly requested via CLI.
- No network calls.
- Use logging module with levels; provide --verbose.

==================================================================== 12) Implementation detail: extract tagset from annotated DB
Implement a function:
discover_tagset(annotated_db_path) -> Set[str]

- Scan text columns that likely contain XML
- Extract element names via regex: r"<\s*([a-zA-Z\_][\w\-]*)"
- Exclude wrapper tags: tafsir_section, tafsir_section_block, tafsir_chunk
- Return sorted set; write to out/tagset\_{book}.json

Use this tagset as allowed tags for validation and training.

====================================================================
Deliver output
====================================================================
You must implement the full subsystem described above with complete code files, tests, and docs. Ensure the CLI can:

- Build a dataset for a given book from the repo DBs
- Validate and report
- Train/eval/infer (even if training is heavy, code must be correct)

Do the work directly in tools/tafsir_student/ with all files created as specified.
