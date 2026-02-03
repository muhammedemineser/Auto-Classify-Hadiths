#!/usr/bin/env python3
import argparse
import re
from typing import List, Set, Tuple

# ---------------- Regex ----------------

BLOCK_START_RE = re.compile(r"^\s*\[?\s*(\d+)\s*-\s*")

# NUR diese Regex wurde zuvor angepasst: auch () erlaubt
MATN_QUOTE_RE = re.compile(r"[\"«(](.*?)[\"»)]")
MATN_QALA_RE = re.compile(r"قال\s*:?\s*(.*)")

META_CUTOFF_RE = re.compile(
    r"\b(رواه|أخرجه|قال الألباني|إسناده|سنده|رجاله|صحيح|ضعيف)\b"
)

# ---------------- Normalisierung ----------------

ARABIC_DIACRITICS_RE = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
TATWEEL = "\u0640"
PUNCT_RE = re.compile(r"[^\w\s\u0600-\u06FF]")
WHITESPACE_RE = re.compile(r"\s+")

def normalize(text: str) -> str:
    text = text.replace(TATWEEL, "")
    text = ARABIC_DIACRITICS_RE.sub("", text)
    text = PUNCT_RE.sub(" ", text)
    text = WHITESPACE_RE.sub(" ", text)
    return text.strip()

# ---------------- MATN extrahieren ----------------

def extract_matn(block: str) -> str:
    quotes = MATN_QUOTE_RE.findall(block)
    if quotes:
        matn = " ".join(quotes)
    else:
        m = MATN_QALA_RE.search(block)
        if not m:
            return ""
        matn = m.group(1)

    matn = META_CUTOFF_RE.split(matn)[0]
    return normalize(matn)

# ---------------- N-Grams ----------------

def ngrams(tokens: List[str], n: int) -> Set[Tuple[str, ...]]:
    if n <= 0 or len(tokens) < n:
        return set()
    return {tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1)}

# ---------------- Blöcke lesen ----------------

def read_blocks(path: str) -> List[Tuple[int, str, List[str], Set[Tuple[str, ...]]]]:
    """
    Returns: (id, full_block, matn_tokens, matn_ngrams)
    """
    blocks = []
    current_id = None
    buf: List[str] = []

    def flush():
        nonlocal current_id, buf
        if current_id is not None and buf:
            block_text = "".join(buf)
            matn = extract_matn(block_text)
            tokens = matn.split()
            blocks.append((current_id, block_text, tokens, set()))
        current_id = None
        buf = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            m = BLOCK_START_RE.match(line)
            if m:
                flush()
                current_id = int(m.group(1))
                buf.append(line)
            else:
                if current_id is not None:
                    buf.append(line)
        flush()

    return blocks

# ---------------- Main ----------------

def main():
    ap = argparse.ArgumentParser(
        description="Remove whole hadith blocks from A if their MATN overlaps with MATN in B (n-gram match)."
    )
    ap.add_argument("--a", required=True, help="Main hadith file (blocks)")
    ap.add_argument("--b", required=True, help="Reference hadith file (blocks)")
    ap.add_argument("--out", default="result.txt", help="Output file")
    ap.add_argument("--min-words", type=int, default=4, help="n-gram size for matching")

    args = ap.parse_args()
    n = args.min_words

    blocks_a = read_blocks(args.a)
    blocks_b = read_blocks(args.b)

    # Build one big n-gram set from B MATNs
    b_ngrams_all: Set[Tuple[str, ...]] = set()
    b_count_matn = 0
    for _, _, tokens, _ in blocks_b:
        if len(tokens) >= n:
            b_count_matn += 1
            b_ngrams_all |= ngrams(tokens, n)

    removed = 0
    kept = 0

    with open(args.out, "w", encoding="utf-8") as out:
        for hid, block_text, a_tokens, _ in blocks_a:
            if len(a_tokens) < n:
                # zu kurz für n-gram match -> behalten
                out.write(block_text)
                if not block_text.endswith("\n"):
                    out.write("\n")
                out.write("\n")
                kept += 1
                continue

            a_ngrams = ngrams(a_tokens, n)

            # REMOVE if any overlap with B
            if a_ngrams & b_ngrams_all:
                removed += 1
                continue

            out.write(block_text)
            if not block_text.endswith("\n"):
                out.write("\n")
            out.write("\n")
            kept += 1

    print(f"B blocks with usable matn (>= {n} words): {b_count_matn}")
    print(f"Total unique B ngrams: {len(b_ngrams_all)}")
    print(f"Blocks kept   : {kept}")
    print(f"Blocks removed: {removed}")
    print(f"Output written to: {args.out}")

if __name__ == "__main__":
    main()
