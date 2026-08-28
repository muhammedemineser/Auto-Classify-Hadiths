"""
Frame-Erkennung fuer Hadith-Matns im normalisierten Raum.

Ziel: Ueberlieferungs-Rahmen (Isnad-Fragmente, Narration-Praefixe/-Suffixe,
Ehrungsformeln) erkennen, damit sie im HASM-Scoring neutralisiert werden
koennen (Weight -> 0). Der Kern-Matn bleibt unbeeinflusst.

Die Frames sind empirisch aus den 6 Kutub-DBs abgeleitet
(Frequenzanalyse der normalisierten Matns) und muessen im NORMALISIERTEN
Raum angegeben werden (siehe utils.Utils.norm).
"""

from __future__ import annotations

# Hierarchisch: laengste Phrasen zuerst, damit Greedy-Matching nicht
# nur Praefixe einzelner Woerter abgreift.
# Alle Strings sind normalisiert (keine Diakritika, unifizierte Buchstaben).
FRAME_PHRASES: tuple[str, ...] = (
    # --- Ehrungs-/Segensformeln (kommen haeufig auch im Albani-txt vor) ---
    "صلي الله عليه وسلم",
    "رضي الله عنهما",
    "رضي الله عنهن",
    "رضي الله عنهم",
    "رضي الله عنها",
    "رضي الله عنه",
    "عليه السلام",
    "تبارك وتعالي",
    "سبحانه وتعالي",
    "عز وجل",
    # --- Narration-Praefixe (matn-seitig) ---
    "قال رسول الله صلي الله عليه وسلم",
    "قال النبي صلي الله عليه وسلم",
    "عن النبي صلي الله عليه وسلم قال",
    "عن رسول الله صلي الله عليه وسلم قال",
    "سمعت رسول الله صلي الله عليه وسلم يقول",
    "سمعت النبي صلي الله عليه وسلم يقول",
    "قال رسول الله",
    "قال النبي",
    "عن رسول الله",
    "عن النبي",
    "سمعت رسول الله",
    "سمعت النبي",
    # --- Gottesspruch-Rahmen ---
    "قال الله تبارك وتعالي",
    "قال الله عز وجل",
    "قال الله تعالي",
    "قال الله",
    # --- Isnad-Verben / Ueberlieferungsklauseln ---
    "حدثنا",
    "اخبرنا",
    "انبانا",
    "حدثني",
    "اخبرني",
    "قال حدثنا",
    "ح و",
    # --- Suffix-/Intro-Klauseln ---
    "وفي الباب عن",
    "وفي رواية",
    "في رواية",
    "رواه",
    "قال ابو داود",
    "قال ابو عيسي",
)

# Hinweis: Einzelne "قال" / "بن" / "ابن" werden bewusst NICHT als Frame
# gewertet, weil sie zu oft Teil des echten Matns sind (false negatives).

# Vorberechnete Token-Listen (normalisiert, gesplittet)
_FRAME_TOKEN_SEQS: tuple[tuple[str, ...], ...] = tuple(
    tuple(p.split()) for p in FRAME_PHRASES
)


def mask_frame_tokens(tokens: list[str]) -> list[bool]:
    """Markiere Frame-Tokens.

    Greedy-Longest-Match ueber die Token-Sequenz. Gibt pro Token True
    (Kern, gewichtet) oder False (Frame, neutral) zurueck.
    """
    if not tokens:
        return []
    n = len(tokens)
    core = [True] * n
    for phrase in _FRAME_TOKEN_SEQS:
        plen = len(phrase)
        if plen == 0:
            continue
        i = 0
        while i <= n - plen:
            if not core[i]:
                i += 1
                continue
            if tuple(tokens[i : i + plen]) == phrase:
                for j in range(i, i + plen):
                    core[j] = False
                i += plen
            else:
                i += 1
    return core


def frame_mask_from_text(normalized_text: str) -> list[bool]:
    return mask_frame_tokens(normalized_text.split())


def count_frames(tokens: list[str]) -> int:
    return sum(0 if m else 1 for m in mask_frame_tokens(tokens))