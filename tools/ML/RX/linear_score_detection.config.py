import os
from pathlib import Path
import ast
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Iterable, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
# Konfiguration für n-gram basierte Wortfolgen-Prüfung (statische Anchors)
#
# Grundprinzip:
#   - Zerlege den Hadith in überlappende n-grams der Länge anchor_n.
#   - Ein Match gilt als gefunden, wenn mindestens hit_rate_threshold der Hadith-Anker
#     exakt im Zieltext vorkommen (binäre Logik statt relativer Scores).
#   - require_prefix steuert, ob beim Hadith der Matn per Prefix-Regeln extrahiert wird.
HADITH_CONFIG = {
    "isnad_comparison": {
        "anchor_n": 3,
        "hit_rate_threshold": 0.7,
        "require_prefix": False,
    },
    "matn_comparison": {  # Haupttext
        "anchor_n": 0.0,
        "hit_rate_threshold": 0.95,
        "require_prefix": True,
    },
}


"""Generelle Config"""

# Konfiguration für n-gram basierte Ähnlichkeitsprüfung

# ============================================================================
# GRUNDPRINZIP: n = Anzahl_Wörter * x
# Wobei: n = Größe der n-grams für den Vergleich
#        x = Skalierungsfaktor (0 < x ≤ 1)
# ============================================================================

NGRAM_CONFIG = {
    # Für sehr kurze Texte (5-15 Wörter)
    "very_short": {
        "x": 0.3,  # 30% der Wortanzahl
        "min_n": 2,  # Minimum bigrams
        "max_n": 4,  # Maximum 4-grams
        "threshold": 0.5,  # 50% Übereinstimmung für Match
        "use_case": "Kurze Sätze, Überschriften",
        "example": "10 Wörter → n=3 (trigrams)",
    },
    # Für kurze Texte (15-50 Wörter)
    "short": {
        "x": 0.25,  # 25% der Wortanzahl
        "min_n": 3,
        "max_n": 8,
        "threshold": 0.6,  # 60% Übereinstimmung
        "use_case": "Einzelne Hadith-Sätze, kurze Absätze",
        "example": "30 Wörter → n=7-8 (7-8-grams)",
    },
    # Für mittlere Texte (50-150 Wörter)
    "medium": {
        "x": 0.2,  # 20% der Wortanzahl
        "min_n": 5,
        "max_n": 15,
        "threshold": 0.65,  # 65% Übereinstimmung
        "use_case": "Mittellange Hadithe, Absätze",
        "example": "100 Wörter → n=20 (würde auf max_n=15 begrenzt)",
    },
    # Für lange Texte (150-500 Wörter)
    "long": {
        "x": 0.15,  # 15% der Wortanzahl
        "min_n": 8,
        "max_n": 25,
        "threshold": 0.7,  # 70% Übereinstimmung
        "use_case": "Lange Hadithe mit Kontext, mehrere Absätze",
        "example": "300 Wörter → n=45 (würde auf max_n=25 begrenzt)",
    },
    # Für sehr lange Texte (500+ Wörter)
    "very_long": {
        "x": 0.1,  # 10% der Wortanzahl
        "min_n": 10,
        "max_n": 30,
        "threshold": 0.75,  # 75% Übereinstimmung
        "use_case": "Vollständige Dokumente, Sammlungen",
        "example": "1000 Wörter → n=100 (würde auf max_n=30 begrenzt)",
    },
}

# ============================================================================
# ÄHNLICHKEITSMETRIKEN - Wähle basierend auf deinem Anwendungsfall
# ============================================================================

SIMILARITY_METRICS = {
    "jaccard": {
        "formula": "intersection / union",
        "range": "0.0 - 1.0",
        "threshold_low": 0.3,  # Schwache Ähnlichkeit
        "threshold_medium": 0.5,  # Moderate Ähnlichkeit
        "threshold_high": 0.7,  # Starke Ähnlichkeit
        "threshold_plagiarism": 0.8,  # Sehr starke Ähnlichkeit (Plagiatsverdacht)
        "best_for": "Ausgeglichene Bewertung, gut für verschiedene Textlängen",
    },
    "dice": {
        "formula": "2 * intersection / (len(set1) + len(set2))",
        "range": "0.0 - 1.0",
        "threshold_low": 0.4,
        "threshold_medium": 0.6,
        "threshold_high": 0.75,
        "threshold_plagiarism": 0.85,
        "best_for": "Gibt höhere Werte als Jaccard, bevorzugt gemeinsame Elemente",
    },
    "cosine": {
        "formula": "dot_product / (norm1 * norm2)",
        "range": "0.0 - 1.0",
        "threshold_low": 0.5,
        "threshold_medium": 0.7,
        "threshold_high": 0.85,
        "threshold_plagiarism": 0.9,
        "best_for": "Wenn Worthäufigkeiten wichtig sind (mit TF-IDF)",
    },
    "overlap": {
        "formula": "intersection / min(len(set1), len(set2))",
        "range": "0.0 - 1.0",
        "threshold_low": 0.5,
        "threshold_medium": 0.7,
        "threshold_high": 0.85,
        "threshold_plagiarism": 0.95,
        "best_for": "Erkennen wenn ein Text Teilmenge eines anderen ist",
    },
}

# ============================================================================
# PRAKTISCHE IMPLEMENTIERUNG
# ============================================================================


def calculate_n_value(word_count, text_category="medium"):
    """
    Berechnet den optimalen n-Wert für n-grams basierend auf Textlänge
    """
    config = NGRAM_CONFIG[text_category]

    # Berechne n = word_count * x
    n = int(word_count * config["x"])

    # Begrenze auf min/max Werte
    n = max(config["min_n"], min(n, config["max_n"]))

    return n


def get_text_category(word_count):
    """
    Bestimmt die Textkategorie basierend auf Wortanzahl
    """
    if word_count < 15:
        return "very_short"
    elif word_count < 50:
        return "short"
    elif word_count < 150:
        return "medium"
    elif word_count < 500:
        return "long"
    else:
        return "very_long"


# ============================================================================
# BEISPIELE FÜR VERSCHIEDENE ANWENDUNGSFÄLLE
# ============================================================================

EXAMPLES = {
    "strict_duplicate_detection": {
        "description": "Suche nach fast exakten Duplikaten",
        "x_values": [0.3, 0.4],  # Größere n-grams
        "metric": "jaccard",
        "threshold": 0.85,
    },
    "paraphrase_detection": {
        "description": "Erkennen von umformulierten Texten",
        "x_values": [0.15, 0.25],  # Kleinere n-grams für mehr Flexibilität
        "metric": "dice",
        "threshold": 0.6,
    },
    "similar_content_finding": {
        "description": "Finden ähnlicher Inhalte (nicht exakte Duplikate)",
        "x_values": [0.2, 0.3],
        "metric": "jaccard",
        "threshold": 0.5,
    },
    "hadith_chain_comparison": {
        "description": "Vergleich von Überlieferungsketten (Isnad)",
        "x_values": [0.25, 0.35],
        "metric": "overlap",
        "threshold": 0.7,
    },
}

# ============================================================================
# Daten für Hadith und Quran Erkennung
# ============================================================================
# Qutation markers
PUNCT_SKIP = {":", "؛", "،", "»", "«", ".", "(", ")", "[", "]", "{", "}", "-", "—"}
# Quran DB Pfad
quran_path = Path("tools/ML/Data/quran").resolve()
try:
    QURAN_PATH_DEFAULT = quran_path.relative_to(REPO_ROOT).with_suffix(".db")
except ValueError:
    pass
# Quran DB Pfad
hadith_books = ["Bukhari", "Muslim", "AbuDaud", "Tirmizi", "Nesai", "IbnMajah"]
HADITH_PATH_DEFAULT = []
for book in hadith_books:
    hadith_path = Path(f"tools/ML/Data/normalized_hadith/{book}")
    full_path = REPO_ROOT / hadith_path
    HADITH_PATH_DEFAULT.append(full_path.relative_to(REPO_ROOT).with_suffix(".db"))
print(HADITH_PATH_DEFAULT)
