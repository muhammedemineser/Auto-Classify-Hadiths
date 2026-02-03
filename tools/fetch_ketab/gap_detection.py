import re
from typing import List, Optional


def _normalize(text: str) -> str:
    return " ".join(text.split()).strip()


def _leading_number(text: str) -> Optional[int]:
    match = re.match(r"^\s*(\d+)", text)
    return int(match.group(1)) if match else None


def _find_number(text: str, number: int, start_pos: int = 0) -> Optional[re.Match]:
    pattern = re.compile(rf"(?<!\d){number}(?!\d)")
    return pattern.search(text, start_pos)


def apply_gap_detection(blocks: List[str], label: str = "") -> List[str]:
    """Ensure hadith numbers stay sequential by looking for missing numbers inside blocks.

    When a gap is detected (e.g. 2509 -> 2511), the function searches the affected
    block with a relaxed pattern to locate the missing number and split the block at
    that position. If multiple numbers are embedded in one block, it splits them into
    separate entries so the consumer can proceed normally afterwards.
    """
    cleaned = [_normalize(b) for b in blocks if _normalize(b)]
    fixed: List[str] = []
    last: Optional[int] = None
    idx = 0

    while idx < len(cleaned):
        block = cleaned[idx]
        number = _leading_number(block)

        if number is None:
            if last is None or not fixed:
                fixed.append(block)
            else:
                fixed[-1] = f"{fixed[-1]} {block}".strip()
            idx += 1
            continue

        if last is not None and number > last + 1:
            missing = last + 1
            relaxed_hit = _find_number(block, missing)

            if relaxed_hit:
                prefix = _normalize(block[: relaxed_hit.start()])
                suffix = _normalize(block[relaxed_hit.start() :])

                if prefix and fixed:
                    fixed[-1] = f"{fixed[-1]} {prefix}".strip()

                cleaned[idx] = suffix

                if label:
                    print(
                        f"[gap-detection] {label}: Fehlende Nummer {missing} im aktuellen Block gefunden, teile Text neu."
                    )

                continue
            else:
                if label:
                    print(
                        f"[gap-detection] {label}: Luecke zwischen {last} und {number}, fehlende {missing} nicht im Block gefunden."
                    )

        fixed.append(block)
        last = number

        # Pruefe, ob innerhalb des Blocks direkt die naechste Nummer sitzt (mehrere Nummern in einem Text)
        while True:
            expected_next = last + 1
            inner_hit = _find_number(block, expected_next, start_pos=1)

            if inner_hit and inner_hit.start() > 0:
                before = _normalize(block[: inner_hit.start()])
                after = _normalize(block[inner_hit.start() :])

                if not before or not after:
                    break

                fixed[-1] = before
                cleaned.insert(idx + 1, after)

                if label:
                    print(
                        f"[gap-detection] {label}: Block zusaetzlich bei {expected_next} geteilt, um Reihenfolge zu sichern."
                    )

                break
            else:
                break

        idx += 1

    return fixed
