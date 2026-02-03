import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from gap_detection import apply_gap_detection

# --- Konfiguration ---
book_name = "taraju"
book_id = 102882
SCROLL_PAUSE = 3.5

# Keywords für die finale Entscheidung (Last-Word-Wins innerhalb der Klammer)
KEYWORDS_AUTH = [
    "صححه",
    "حسنه",
    "قواه",
    "الصحيحة",
    "صحيح",
    "حسنت",
    "صححت",
    "تصحيحه",
    "تحسينه",
]
KEYWORDS_SCHWACH = [
    "ضعفه",
    "ضعفها",
    "الضعيفة",
    "منكر",
    "انقطاع",
    "بوضعه",
    "ضعفت",
    "تضعيفه",
]


def bestimme_kategorie(block_text):
    # Sucht die letzte [...] Klammer, die das Wort "تراجع" enthält
    klammern = re.findall(r"\[([^\]]*تراجع[^\]]*)\]", block_text)
    if not klammern:
        return None

    finaler_inhalt = klammern[-1]
    funde = []
    for word in KEYWORDS_AUTH:
        for m in re.finditer(word, finaler_inhalt):
            funde.append((m.start(), "authentisch"))
    for word in KEYWORDS_SCHWACH:
        for m in re.finditer(word, finaler_inhalt):
            funde.append((m.start(), "schwach"))

    if not funde:
        return None
    funde.sort(key=lambda x: x[0])
    return funde[-1][1]


# --- Browser Setup ---
options = Options()
options.add_argument("--start-maximized")
options.add_argument("--headless=new")  # Diese Zeile einkommentieren
options.add_argument("--disable-gpu")  # Deaktiviert die Hardwarebeschleunigung
driver = webdriver.Chrome(options=options)

try:
    base_url = f"https://ketabonline.com/ar/books/{book_id}/read?part=1?page=2"
    driver.get(base_url)
    wait = WebDriverWait(driver, 25)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "p.g-paragraph")))

    # --- Flüssiges Scrollen ---
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script(
            "window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'});"
        )
        time.sleep(SCROLL_PAUSE)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        print(f"Lade Daten... Höhe: {new_height}", end="\r")

    # --- Blockweise Extraktion ---
    paragraphs = driver.find_elements(
        By.CSS_SELECTOR, f"p.g-paragraph.g-rtl.p-ctrl[id^='p-{book_id}-']"
    )

    blocks = []
    current_block = []

    for p in paragraphs:
        # Prüfen, ob dieser Absatz ein <span class="g-list"> enthält
        try:
            span_list = p.find_elements(By.CSS_SELECTOR, "span.g-list")
            # Wenn ein g-list Span existiert und mit einer Zahl beginnt -> Neuer Block
            is_new_start = False
            if span_list:
                span_text = span_list[0].text.strip()
                if re.match(r"^\d+", span_text):
                    is_new_start = True

            if is_new_start:
                if current_block:
                    blocks.append(" ".join(current_block))
                current_block = [p.text.strip()]
            else:
                current_block.append(p.text.strip())
        except:
            current_block.append(p.text.strip())

    # Letzten Block sichern
    if current_block:
        blocks.append(" ".join(current_block))

    blocks = apply_gap_detection(blocks, label=book_name)

    # --- Speichern ---
    with open(f"{book_name}_authentisch.txt", "w", encoding="utf-8") as f_auth, open(
        f"{book_name}_schwach.txt", "w", encoding="utf-8"
    ) as f_schwach:

        count_a, count_s = 0, 0
        for block in blocks:
            # Bereinigung von überflüssigen Leerzeichen im Block
            clean_block = " ".join(block.split())
            kategorie = bestimme_kategorie(clean_block)

            if kategorie == "authentisch":
                f_auth.write(clean_block + "\n")
                count_a += 1
            elif kategorie == "schwach":
                f_schwach.write(clean_block + "\n")
                count_s += 1

    print(f"\n✅ Analyse fertig!")
    print(f"   - Authentisch (Sahih/Hasan): {count_a}")
    print(f"   - Schwach (Da'if/Munkar): {count_s}")

except Exception as e:
    print(f"\n❌ Fehler: {e}")
finally:
    driver.quit()
