import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- Konfiguration ---
book_name = "tafsir"
book_id = 24539
SCROLL_PAUSE = 3.5

base_url = f"https://ketabonline.com/ar/books/{book_id}/read?part=1?page=2"

# --- Browser Setup ---
options = Options()
options.add_argument("--start-maximized")
options.add_argument("--headless=new")  # Diese Zeile einkommentieren
options.add_argument("--disable-gpu")  # Deaktiviert die Hardwarebeschleunigung
driver = webdriver.Chrome(options=options)

try:
    print(f"\n--- Starte präzise Extraktion: {book_name} (ID: {book_id}) ---")
    driver.get(base_url)
    wait = WebDriverWait(driver, 25)

    # Warten, bis das erste Element mit diesen exakten Klassen da ist
    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "p.g-paragraph.g-rtl.p-ctrl"))
    )

    # --- Scroll-Logik (Flüssig) ---
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
        print(f"Scrolle... Höhe: {new_height}", end="\r")

    # --- Präzise Auswahl ---
    # Selektiert p-Tags mit allen 3 Klassen und einer ID, die mit "p-{book_id}" beginnt
    selector = f"p.g-paragraph.g-rtl.p-ctrl[id^='p-{book_id}-']"
    elements = driver.find_elements(By.CSS_SELECTOR, selector)

    if not elements:
        print("⚠️ Keine passenden Elemente gefunden. Prüfe den Selektor.")
    else:
        filename = f"{book_name}_p_tags.txt"
        with open(filename, "w", encoding="utf-8") as f:
            count = 0
            for el in elements:
                # Wir holen die ID für eventuelle Fehlersuche (optional)
                tag_id = el.get_attribute("id")
                text_content = el.text

                if text_content:
                    # Bereinigt den Text (entfernt Zeilenumbrüche innerhalb des Verses)
                    clean_line = " ".join(text_content.split()).strip()

                    # Speichert nur den Text
                    f.write(f"{clean_line}\n")
                    count += 1

        print(f"\n✅ Fertig! {count} präzise Elemente in '{filename}' gespeichert.")

except Exception as e:
    print(f"\n❌ Fehler: {e}")

finally:
    driver.quit()
