from transformers import pipeline
from transformers import pipeline
from arabert.preprocess import ArabertPreprocessor
from arabic_reshaper import reshape
from bidi.algorithm import get_display
import warnings

# Warnungen unterdrücken
warnings.filterwarnings("ignore")

def d(text):
    return get_display(reshape(text))

# استخدام نموذج Zero-Shot قوي يدعم العربية
classifier = pipeline("zero-shot-classification", model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli")

def analyze_rijal(text):
    # Optimierte Labels, die technischer und weniger emotional sind
    candidate_labels = [
        "راوي موثوق ومقبول",    # Zuverlässiger und akzeptierter Überlieferer
        "راوي ضعيف ومرفوض",    # Schwacher und abgelehnter Überlieferer
        "راوي مجهول أو غير معروف" # Unbekannter oder anonymer Überlieferer
    ]

    # Der wichtigste Teil: Die Hypothese muss den Kontext schärfen!
    # Wir sagen dem Modell explizit, dass es um die Bewertung von Personen geht.
    hypothesis_template = "درجة هذا الشخص في نقل الحديث هي أنه {}"
    
    result = classifier(text, candidate_labels, hypothesis_template=hypothesis_template)
    
    top_label = result['labels'][0]
    score = result['scores'][0]
    
    print(f"\n {d("المصطلح")}: {d(text)}")
    print(f"{d("التصنيف")}: {d(top_label)} ({d("الدقة")}: {score:.2%})")

# تجربة المصطلحات التي فشل فيها النموذج السابق
terms = [
    # 1. Höchstes Lob (Sollte 99% Ta'diil sein)
    "ثقة ثبت حجة",
    
    # 2. Das Problem-Beispiel (Sprachlich negativ "ba's", technisch positiv)
    "ليس به بأس",
    
    # 3. Höchste Kritik (Sollte 99% Jarh sein)
    "دجال وضع الحديث",
    
    # 4. Subtile Kritik (Klingt fast neutral, ist aber Jarh)
    "تعرف وتنكر",
    
    # 5. Relative Schwäche (Oft missverstanden)
    "ليس بالقوي",
    
    # 6. Lob der Ehrlichkeit, aber Kritik am Gedächtnis (Komplex)
    "صدوق له أوهام",
    
    # 7. Absolutes Urteil über das Gedächtnis
    "سيئ الحفظ جدا",
    
    # 8. Unklarer Status
    "مستور",
    
    # 9. Sprachlich großartig, technisch schwächer als 'Thiqah'
    "شيخ صالح",
    
    # 10. Die "Todes-Urteile"
    "متروك الحديث",
    "ذاهب الحديث"
]

for t in terms:
    analyze_rijal(t)