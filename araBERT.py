from transformers import pipeline
from arabert.preprocess import ArabertPreprocessor
from arabic_reshaper import reshape
from bidi.algorithm import get_display
import warnings

# Warnungen unterdrücken
warnings.filterwarnings("ignore")

def d(text):
    return get_display(reshape(text))

# NEUES MODELL: Dieses ist sehr verbreitet und meist offen zugänglich
model_name = "asafaya/bert-base-arabic"

print("Initialisiere Preprocessor...")
# Wir nutzen hier die passende AraBERT-Version für das Modell
arabert_prep = ArabertPreprocessor(model_name="bert-base-arabert")

print(f"Lade Modell: {model_name}...")
try:
    nlp_sentiment = pipeline("sentiment-analysis", model=model_name)
    
    def analyze_hadith(text):
        clean_text = arabert_prep.preprocess(text)
        result = nlp_sentiment(clean_text)[0]
        print(f"\nHadith: {d(text)}")
        # Mapping: Label_0 = Neutral, Label_1 = Positive, Label_2 = Negative
        # (Kann je nach Modell variieren)
        print(f"Sentiment: {result['label']} (Score: {result['score']:.4f})")

    # Test
    # --- Ta'diil (Lob & Zuverlässigkeit) ---
    analyze_hadith("ثقة ثبت")               # Höchste Stufe der Zuverlässigkeit
    analyze_hadith("إمام حجة")               # Ein Vorbild und Beweis
    analyze_hadith("صدوق حسن الحديث")       # Ehrlich, seine Hadithe sind gut
    analyze_hadith("حافظ متقن")              # Ein präziser Bewahrer

    # --- Jarh (Kritik & Schwäche) ---
    analyze_hadith("كذاب يضع الحديث")        # Ein Lügner, der Hadithe erfindet
    analyze_hadith("متروك الحديث")           # Seine Hadithe werden verworfen
    analyze_hadith("سيئ الحفظ")              # Schlechtes Gedächtnis
    analyze_hadith("فيه ضعف")                # In ihm ist Schwäche
    analyze_hadith("منكر الحديث")            # Seine Überlieferungen sind missbilligt

    # --- Grenzfälle & Nuancen ---
    analyze_hadith("ليس به بأس")             # "Es ist nichts gegen ihn einzuwenden" (Lob)
    analyze_hadith("شيخ")                    # Ein "Scheich" (oft neutral/leichtes Lob)
    analyze_hadith("مجهول")                  # Unbekannt (Neutral/Status unklar)
    analyze_hadith("ضعيف يكتب حديثه")        # Schwach, aber seine Hadithe werden (zur Prüfung) notiert
except Exception as e:
    print(f"\nFehler beim Laden des Modells: {e}")
