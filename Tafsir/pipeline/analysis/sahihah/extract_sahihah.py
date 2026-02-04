#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import json
import os
from pathlib import Path

IN_PATH = Path(
    os.environ.get(
        "IN_SITTAH_PATH",
        "/app/Tafsir/pipeline/analysis/sahihah/in_sittah.txt",
    )
)

OUT_PATH = Path(
    "/app/Tafsir/pipeline/analysis/sahihah/sahihah_hadith_extracted_in_sittah.txt"
)

# Matches the first "sequence-like" number at the beginning area of the line:
# - optionally preceded by a short intro text
# - must be the first number on the line (we enforce: no digits before it)
# - placed "far in front" (we only search near the start)
NUM_RE = re.compile(r"^\s*([^\d]{0,80})\s*(\d{1,5})\b", re.UNICODE)
KUTUB_LIST_MARKER = "\tKUTUBS="

AL_OPT = r"(?:ال)?"
KUTUB_PATTERNS = {
    "Bukhari": rf"(?:{AL_OPT}بخاري|صحيح\s*{AL_OPT}بخاري|{AL_OPT}بخاري\s*في\s*صحيحه|{AL_OPT}بخاري\s*في\s*ال?صحيح)",
    "Muslim": rf"(?:{AL_OPT}مسلم|صحيح\s*{AL_OPT}مسلم|{AL_OPT}مسلم\s*في\s*صحيحه|{AL_OPT}مسلم\s*في\s*ال?صحيح)",
    "AbuDaud": rf"(?:أبو\s*داود|ابو\s*داود|سنن\s*أبي\s*داود|سنن\s*ابى\s*داود|سنن\s*ابو\s*داود)",
    "Tirmizi": rf"(?:{AL_OPT}ترمذي|{AL_OPT}ترمذى|سنن\s*{AL_OPT}ترمذي|جامع\s*{AL_OPT}ترمذي|{AL_OPT}جامع\s*{AL_OPT}ترمذي|{AL_OPT}جامع\s*للترمذي|{AL_OPT}الجامع\s*للترمذي)",
    "Nesai": rf"(?:{AL_OPT}نسائي|{AL_OPT}نسائى|سنن\s*{AL_OPT}نسائي|سنن\s*{AL_OPT}نسائى|{AL_OPT}مجتبى|{AL_OPT}سنن\s*الصغرى|السنن\s*الصغرى)",
    "IbnMajah": rf"(?:ابن\s*ماجه|ابن\s*ماجة|سنن\s*ابن\s*ماجه|سنن\s*ابن\s*ماجة)",
}
KUTUB_PATTERNS_RE = {
    key: re.compile(pattern, flags=re.UNICODE) for key, pattern in KUTUB_PATTERNS.items()
}

def extract_balanced_segment(s: str, start_idx: int, open_ch: str, close_ch: str):
    """
    Extracts a balanced segment starting at start_idx where s[start_idx] == open_ch.
    Supports nested open/close of same type.
    Returns (segment_text_including_delims, end_idx_exclusive) or (None, None).
    """
    if start_idx < 0 or start_idx >= len(s) or s[start_idx] != open_ch:
        return None, None

    depth = 0
    i = start_idx
    while i < len(s):
        ch = s[i]
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return s[start_idx : i + 1], i + 1
        i += 1

    return None, None


def split_kutub_list(line: str):
    if KUTUB_LIST_MARKER not in line:
        return line, None
    base, raw = line.rsplit(KUTUB_LIST_MARKER, 1)
    raw = raw.strip()
    if not raw:
        return base, None
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return base, data
    except Exception:
        return base, None
    return base, None

def detect_kutub_list(line: str):
    hits = []
    for key, rx in KUTUB_PATTERNS_RE.items():
        if rx.search(line):
            hits.append(key)
    if not hits:
        return None
    return sorted(set(hits))
def extract_hadith_text(line: str):
    """
    Returns (hadith_number:int, hadith_text:str) or (None, None) if not parseable.
    Rules:
    - find the first number near the start, which is the first number on the line
    - if number < 3000 -> hadith enclosed by double quotes (")
    - if number >= 3000 -> hadith enclosed by parentheses (...) with nesting supported
    """
    m = NUM_RE.match(line)
    if not m:
        return None, None

    num_str = m.group(2)
    try:
        num = int(num_str)
    except ValueError:
        return None, None

    rest = line[m.end() :]

    if num < 3000:
        # Hadith in double quotes. Allow inner quotes by supporting doubled quotes ("")
        # and backslash-escaped quotes (\") without breaking the match.
        # We extract the first quoted block after the number.
        q_start = rest.find('"')
        if q_start == -1:
            return num, ""

        i = q_start + 1
        buf = []
        while i < len(rest):
            ch = rest[i]
            if ch == "\\":
                if i + 1 < len(rest):
                    buf.append(rest[i + 1])
                    i += 2
                    continue
            if ch == '"':
                # Treat "" as an embedded quote
                if i + 1 < len(rest) and rest[i + 1] == '"':
                    buf.append('"')
                    i += 2
                    continue
                # closing quote
                return num, "".join(buf).strip()
            buf.append(ch)
            i += 1

        # Unclosed quote -> return whatever captured
        return num, "".join(buf).strip()

    else:
        # Hadith in parentheses with nesting
        p_start = rest.find("(")
        if p_start == -1:
            return num, ""

        seg, _end = extract_balanced_segment(rest, p_start, "(", ")")
        if not seg:
            return num, ""

        # remove outer parentheses
        inner = seg[1:-1].strip()
        return num, inner


def main():
    if not IN_PATH.exists():
        raise FileNotFoundError(str(IN_PATH))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    last_num = -1
    out_lines = []

    with IN_PATH.open("r", encoding="utf-8", errors="replace") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            if not line.strip():
                continue

            base_line, kutub_list = split_kutub_list(line)
            num, hadith = extract_hadith_text(base_line)
            if num is None:
                continue
            if not kutub_list:
                kutub_list = detect_kutub_list(base_line)
            # Sequence order must not decrease
            if last_num != -1 and num < last_num:
                continue

            last_num = num
            if kutub_list:
                out_lines.append(
                    f"{num}\t{hadith}{KUTUB_LIST_MARKER}{json.dumps(kutub_list, ensure_ascii=False)}"
                )
            else:
                out_lines.append(f"{num}\t{hadith}")

    with OUT_PATH.open("w", encoding="utf-8") as w:
        w.write("\n".join(out_lines) + ("\n" if out_lines else ""))


if __name__ == "__main__":
    main()
