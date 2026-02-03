#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import shorten
from typing import Iterable, List, TextIO

try:  # Support running as module and as standalone script
    from .filter_blocks_by_hadith_occurrence import HadithEntry, load_hadith_entries
except ImportError:  # pragma: no cover
    from filter_blocks_by_hadith_occurrence import HadithEntry, load_hadith_entries

try:
    from .matn_utils import matn_tokens_for_matching, tokenize
except ImportError:  # pragma: no cover
    from matn_utils import matn_tokens_for_matching, tokenize


# def format_snippet(text: str) -> str:
#     return shorten(text.replace("\n", " "), width=120, placeholder="…")


def describe_entry(
    entry: HadithEntry,
    index: int,
    tokens: List[str],
    matn_tokens: List[str],
    require_prefix: bool,
    skip_span_detection: bool,
    output_file: TextIO = None,
) -> None:
    header = (
        f"Entry {index} – {entry.get('source') or 'unknown'}:{entry.get('line_number')}"
    )

    lines = [
        header,
        "-" * len(header),
        f"Raw tokens      : {len(tokens)}",
        f"Extracted tokens: {len(matn_tokens)}",
        f"Mode            : prefix={'on' if require_prefix else 'off'}, span_detection={'disabled' if skip_span_detection else 'enabled'}",
        f"Raw text        : {(entry['text'])}",
        f"Matn text       : {' '.join(matn_tokens) or '<empty>'}",
        "",
    ]

    content = "\n".join(lines) + "\n"
    if output_file:
        output_file.write(content)
    else:
        print(content, end="")


def load_entries(paths: Iterable[Path], json_key: str) -> List[HadithEntry]:
    return load_hadith_entries(list(paths), json_value_key=json_key)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect how matn tokens are extracted from raw hadiths.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--hadith",
        "-H",
        dest="hadith",
        action="append",
        nargs="+",
        required=True,
        help="Paths to hadith reference files (JSON, NDJSON, txt).",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Path to the output file where results will be saved.",
    )
    parser.add_argument(
        "--json-key",
        default="text",
        help="Field name to extract when referencing JSON/NDJSON sources.",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=1,
        help="1-based index of the first hadith to display.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=3671,
        help="Maximum number of hadith extractions to inspect.",
    )
    prefix_group = parser.add_mutually_exclusive_group()
    prefix_group.add_argument(
        "--require-prefix",
        dest="require_prefix",
        action="store_true",
        help="Honor matn prefixes when extracting (default behavior).",
    )
    prefix_group.add_argument(
        "--no-prefix",
        dest="require_prefix",
        action="store_false",
        help="Do not require prefixes when slicing the matn window.",
    )
    parser.set_defaults(require_prefix=True)
    parser.add_argument(
        "--skip-span-detection",
        action="store_true",
        help="Do not attempt to capture bracketed spans when prefix matching fails.",
    )
    args = parser.parse_args()

    hadith_paths = [Path(p) for group in args.hadith for p in (group or [])]
    if not hadith_paths:
        parser.error("--hadith is required")

    entries = load_entries(hadith_paths, args.json_key)
    total = len(entries)
    if total == 0:
        parser.exit("No hadiths could be loaded from the given paths.")

    start = max(1, args.start)
    limit = max(1, args.limit)
    displayed = entries[start - 1 : start - 1 + limit]

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(
                f"Loaded {total} hadith entries; inspecting {len(displayed)} starting at #{start}.\n\n"
            )
            for idx, entry in enumerate(displayed, start=start):
                tokens = tokenize(entry["text"])
                matn_tokens = matn_tokens_for_matching(
                    tokens, args.require_prefix, args.skip_span_detection
                )
                describe_entry(
                    entry,
                    idx,
                    tokens,
                    matn_tokens,
                    args.require_prefix,
                    args.skip_span_detection,
                    output_file=f,
                )
        print(f"Results written to {args.output}")
    else:
        print(
            f"Loaded {total} hadith entries; inspecting {len(displayed)} starting at #{start}.\n"
        )
        for idx, entry in enumerate(displayed, start=start):
            tokens = tokenize(entry["text"])
            matn_tokens = matn_tokens_for_matching(
                tokens, args.require_prefix, args.skip_span_detection
            )
            describe_entry(
                entry,
                idx,
                tokens,
                matn_tokens,
                args.require_prefix,
                args.skip_span_detection,
            )


if __name__ == "__main__":
    main()
