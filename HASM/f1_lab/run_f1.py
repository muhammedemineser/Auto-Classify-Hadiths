from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from HASM.ranking import Utils, f1


def main() -> None:
    parser = argparse.ArgumentParser(description="F1 sandbox for HASM.ranking.f1")
    parser.add_argument("--reference", required=True, help="Reference text")
    parser.add_argument("--candidate", required=True, help="Candidate text")
    parser.add_argument("--max-order", type=int, default=2)
    parser.add_argument(
        "--reference-pos-json",
        default=None,
        help='JSON array of precomputed POS tags, e.g. ["noun","verb"]',
    )
    parser.add_argument(
        "--weights-json",
        default=None,
        help="Optional explicit BLEU weights JSON array",
    )
    args = parser.parse_args()

    reference_pos: Optional[list[str]]
    if args.reference_pos_json:
        reference_pos = [str(x) for x in json.loads(args.reference_pos_json)]
    else:
        # For sandbox convenience: derive once from reference text.
        reference_pos = Utils.tag_pos_text(args.reference)

    weights = None
    if args.weights_json:
        weights = [float(x) for x in json.loads(args.weights_json)]

    predictions = [args.candidate]
    references = [[args.reference]]

    result = f1(
        reference=references,
        candidate=predictions,
        wheights=weights,
        max_order=args.max_order,
        reference_pos=reference_pos,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
