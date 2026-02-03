#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

import regex as re

IN_PATH = Path(
    "/home/muhammed-emin-eser/desk/apps/classify/tools/sahihah/sahihah_komplett.txt"
)
OUT_IN_SITTAH = Path(
    "/home/muhammed-emin-eser/desk/apps/classify/tools/sahihah/in_sittah.txt"
)
OUT_OUT_SITTAH = Path(
    "/home/muhammed-emin-eser/desk/apps/classify/tools/sahihah/out_sittah.txt"
)

AL_OPT = r"(?:ال)?"

KUTUB_PATTERNS = {
    "Bukhari": rf"(?:{AL_OPT}بخاري|صحيح\s*{AL_OPT}بخاري|{AL_OPT}بخاري\s*في\s*صحيحه|{AL_OPT}بخاري\s*في\s*ال?صحيح)",
    "Muslim": rf"(?:{AL_OPT}مسلم|صحيح\s*{AL_OPT}مسلم|{AL_OPT}مسلم\s*في\s*صحيحه|{AL_OPT}مسلم\s*في\s*ال?صحيح)",
    "AbuDaud": rf"(?:أبو\s*داود|ابو\s*داود|سنن\s*أبي\s*داود|سنن\s*ابى\s*داود|سنن\s*ابو\s*داود)",
    "Tirmizi": rf"(?:{AL_OPT}ترمذي|{AL_OPT}ترمذى|سنن\s*{AL_OPT}ترمذي|جامع\s*{AL_OPT}ترمذي|{AL_OPT}جامع\s*{AL_OPT}ترمذي|{AL_OPT}جامع\s*للترمذي|{AL_OPT}الجامع\s*للترمذي)",
    "Nesai": rf"(?:{AL_OPT}نسائي|{AL_OPT}نسائى|سنن\s*{AL_OPT}نسائي|سنن\s*{AL_OPT}نسائى|{AL_OPT}مجتبى|{AL_OPT}سنن\s*الصغرى|السنن\s*الصغرى)",
    "IbnMajah": rf"(?:ابن\s*ماجه|ابن\s*ماجة|سنن\s*ابن\s*ماجه|سنن\s*ابن\s*ماجة)",
}

KUTUB_RE = re.compile(
    "|".join(f"(?:{p})" for p in KUTUB_PATTERNS.values()), flags=re.UNICODE
)
KUTUB_PATTERNS_RE = {
    key: re.compile(pattern, flags=re.UNICODE) for key, pattern in KUTUB_PATTERNS.items()
}

KUTUB_LIST_MARKER = "\tKUTUBS="


def classify_chunk(args):
    start_idx, lines = args
    in_hits = []
    out_hits = []
    for i, line in enumerate(lines):
        global_idx = start_idx + i
        if line and KUTUB_RE.search(line):
            hits = []
            for key, rx in KUTUB_PATTERNS_RE.items():
                if rx.search(line):
                    hits.append(key)
            hits = sorted(set(hits))
            if hits:
                line = line + KUTUB_LIST_MARKER + json.dumps(
                    hits, ensure_ascii=False
                )
            in_hits.append((global_idx, line))
        else:
            out_hits.append((global_idx, line))
    return in_hits, out_hits


def main():
    if not IN_PATH.exists():
        raise FileNotFoundError(str(IN_PATH))

    with IN_PATH.open("r", encoding="utf-8", errors="replace") as f:
        lines = [ln.rstrip("\n") for ln in f if ln.strip()]

    n = len(lines)
    if n == 0:
        OUT_IN_SITTAH.write_text("", encoding="utf-8")
        OUT_OUT_SITTAH.write_text("", encoding="utf-8")
        return

    workers = os.cpu_count() or 2
    chunk_size = (n + workers - 1) // workers

    tasks = []
    for start in range(0, n, chunk_size):
        tasks.append((start, lines[start : start + chunk_size]))

    in_all = []
    out_all = []

    with ProcessPoolExecutor(max_workers=workers) as ex:
        for in_part, out_part in ex.map(classify_chunk, tasks):
            in_all.extend(in_part)
            out_all.extend(out_part)

    in_all.sort(key=lambda x: x[0])
    out_all.sort(key=lambda x: x[0])

    OUT_IN_SITTAH.parent.mkdir(parents=True, exist_ok=True)
    OUT_OUT_SITTAH.parent.mkdir(parents=True, exist_ok=True)

    with OUT_IN_SITTAH.open("w", encoding="utf-8") as w_in:
        for _, line in in_all:
            w_in.write(line + "\n")

    with OUT_OUT_SITTAH.open("w", encoding="utf-8") as w_out:
        for _, line in out_all:
            w_out.write(line + "\n")


if __name__ == "__main__":
    main()
