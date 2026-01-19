from transformers import pipeline
from arabert.preprocess import ArabertPreprocessor
from arabic_reshaper import reshape
from bidi.algorithm import get_display
import warnings

# Warnungen unterdrücken
warnings.filterwarnings("ignore")

def d(text):
    if not isinstance(text, str):
        return text
    return get_display(reshape(text))

print("Lade Modell... (bitte warten)")
classifier = pipeline("zero-shot-classification", model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli")

def analyze_rijal_stable(text):
    # Scharfe Kategorien für die KI
    candidate_labels = ["ثقة مقبول", "ضعيف مردود", "مجهول مستور"]
    
    # Kontext-Zuweisung
    hypothesis_template = "هذا الراوي يعتبر {}"
    
    result = classifier(text, candidate_labels, hypothesis_template=hypothesis_template, multi_label=False)
    
    # Logik-Check für die "Todes-Urteile" der Hadith-Wissenschaft
    jarh_keywords = ["كذاب", "دجال", "متروك", "وضاع", "ذاهب"]
    is_hard_jarh = any(word in text for word in jarh_keywords)
    
    label = result['labels'][0]
    score = result['scores'][0]
    
    # Manuelle Korrektur, falls die KI bei Fachbegriffen wie 'Dajjal' patzt
    if is_hard_jarh and label != "ضعيف مردود":
        label = "ضعيف مردود (Korrektur)"
        score = 1.0

    # WICHTIG: d() nur auf Text anwenden, nicht auf den Score!
    print(f"\nTerminus: {d(text)}")
    print(f"Urteil: {d(label)} ({score:.2%})")

# --- DIE ULTIMATIVE BELASTUNGSPROBE ---
terms = [
    # 1. Scheinbarer Widerspruch (Ehrlich, aber macht Fehler)
    "صدوق يخطئ", 
    
    # 2. Lob, das oft missverstanden wird (Nichts gegen ihn einzuwenden)
    "لا بأس به", 
    
    # 3. Höchstes Lob (Übersteigert)
    "إليه المنتهى في التثبت", 
    
    # 4. Technischer Jarh (Klingt wie eine Beschreibung, ist aber Kritik)
    "ليس بذاك", # "Er ist nicht jener (den man sucht)" -> Jarh
    
    # 5. Extrem seltener Begriff (Klingt positiv, ist negativ)
    "مكفوف البصر في الحديث", # "Blind in der Hadith-Wissenschaft"
    
    # 6. Milde Kritik
    "فيه مقال", # "Über ihn gibt es Gerede"
    
    # 7. Lob der Frömmigkeit bei gleichzeitiger Ablehnung der Überlieferung
    "رجل صالح لكنه ليس من أهل هذا الشأن", 
    
    # 8. Der "Lügner"-Euphemismus
    "فيه نظر", # Imam al-Bukhari nutzte dies oft für sehr schwache Leute
    
    # 9. Doppelte Verneinung
    "غير ثقة وغير مأمون",
    
    # 10. Vergleich (Relativität)
    "فلان أوثق منه", # "X ist zuverlässiger als er" (Sagt indirekt etwas über beide aus)
    
    # 11. Vernichtendes Urteil (Sprachlich sehr stark)
    "يسرق الحديث", # "Er stiehlt Hadithe"
    
    # 12. Unklar / Majhul
    "لا يعرف له حال"
]

for t in terms:
    analyze_rijal_stable(t)