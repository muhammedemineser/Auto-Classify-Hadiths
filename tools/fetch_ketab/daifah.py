import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from gap_detection import apply_gap_detection

# --- Konfiguration ---
book_name = "daifah"
book_id = 1423
SCROLL_PAUSE = 3.5

# --- Automatisierungs-Daten ---
start_kapitel = 7
end_kapitel = 14
part_and_pages = {
    7: 5602,
    8: 6325,
    9: 7139,
    10: 7922,
    11: 8922,
    12: 9936,
    13: 10985,
    14: 12166,
}

# --- Browser Setup ---
options = Options()
options.add_argument("--start-maximized")
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
driver = webdriver.Chrome(options=options)

current_kapitel = start_kapitel

try:
    while current_kapitel <= end_kapitel:
        if current_kapitel not in part_and_pages:
            print(f"⚠️ Kapitel {current_kapitel} nicht im Dictionary. Ende.")
            break

        # URL AUTOMATISIERUNG DURCH INKREMENTIEREN
        page_nr = part_and_pages[current_kapitel]
        base_url = f"https://ketabonline.com/ar/books/{book_id}/read?part={current_kapitel}&page={page_nr}"

        print(
            f"\n--- Starte Extraktion: {book_name} | Part: {current_kapitel} (Seite: {page_nr}) ---"
        )
        driver.get(base_url)
        wait = WebDriverWait(driver, 25)

        # --- AB HIER DEINE BESTEHENDE LOGIK (UNVERÄNDERT) ---
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.book-page")))

        # 1. Flüssiges Scrollen
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
            print(f"Scrolle flüssig... Höhe: {new_height}", end="\r")

        # 2. Alle relevanten Paragraphen finden
        paragraphs = driver.find_elements(
            By.CSS_SELECTOR, f"p.g-paragraph.p-ctrl[id^='p-{book_id}-']"
        )

        if not paragraphs:
            print(f"⚠️ Keine Inhalte in Part {current_kapitel} gefunden.")
        else:
            # 3. Block-Logik mit Inkrement und Sonderzeichen
            filename = f"{book_name}.txt"
            hadith_blocks = []
            current_buffer = []
            letzte_nummer = None

            for p in paragraphs:
                text = " ".join(p.text.split()).strip()
                if not text:
                    continue

                match = re.match(r"^\s*(\d+)\s*-?\s*[(\"«]", text)
                gefundene_nr = None
                if match:
                    temp_nr = int(match.group(1))
                    if letzte_nummer is None or temp_nr > letzte_nummer:
                        gefundene_nr = temp_nr

                if gefundene_nr:
                    if current_buffer:
                        hadith_blocks.append(" ".join(current_buffer))
                    current_buffer = [text]
                    letzte_nummer = gefundene_nr
                else:
                    current_buffer.append(text)

            if current_buffer:
                hadith_blocks.append(" ".join(current_buffer))

            hadith_blocks = apply_gap_detection(hadith_blocks, label=book_name)

            # WICHTIG: "a" (Append) statt "w", damit Kapitel angehängt werden
            with open(filename, "a", encoding="utf-8") as f:
                for block in hadith_blocks:
                    f.write(f"{block}\n")
                f.flush()

            print(f"\n✅ Part {current_kapitel} abgeschlossen und gespeichert.")

        # Inkrementieren für die nächste Runde
        current_kapitel += 1

except Exception as e:
    print(f"\n❌ Fehler: {e}")
finally:
    driver.quit()
    print("\n--- Prozess beendet ---")
