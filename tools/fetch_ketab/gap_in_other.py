import re


def check_gaps_in_other_file(gap_log_path, search_file_path):
    # 1. Vermisste Nummern aus dem Log extrahieren
    missing_numbers = set()

    # Regex sucht nach "Erwartet X, aber gefunden: Y" und sammelt alle Zahlen dazwischen
    with open(gap_log_path, "r", encoding="utf-8") as f:
        for line in f:
            match = re.search(r"Erwartet (\d+), aber gefunden: (\d+)", line)
            if match:
                start = int(match.group(1))
                end = int(match.group(2))
                # Füge alle Zahlen der Lücke zur Suchliste hinzu (z.B. 3, 4, 5, 6)
                for nr in range(start, end):
                    missing_numbers.add(nr)

    print(f"🔍 Suche nach insgesamt {len(missing_numbers)} vermissten Nummern...")

    # 2. In der anderen Datei nach diesen Nummern suchen
    found_numbers = set()
    with open(search_file_path, "r", encoding="utf-8") as f:
        content = f.read()
        for nr in list(missing_numbers):
            # Sucht nach "Nr -" am Zeilenanfang in der Zieldatei
            if re.search(rf"^\s*{nr}\s*-", content, re.MULTILINE):
                found_numbers.add(nr)

    # 3. Ergebnis ausgeben
    still_missing = missing_numbers - found_numbers

    print("-" * 30)
    if found_numbers:
        print(f"✅ Gefunden in '{search_file_path}': {sorted(list(found_numbers))}")
    else:
        print("❌ Keine der vermissten Nummern in der Zieldatei gefunden.")

    if still_missing:
        print(f"🚨 Immer noch fehlend: {sorted(list(still_missing))}")
    else:
        print("🎉 Alle Lücken wurden in der anderen Datei gefunden!")


# Anwendung:
# gap_log.txt ist die Datei mit deinen "⚠️ LÜCKE GEFUNDEN!" Meldungen
# backup.txt ist die Datei, in der du hoffst, dass sie drin sind
check_gaps_in_other_file(
    "/home/muhammed-emin-eser/desk/apps/fetch_ketab/sahihah/fehlt.txt",
    "/home/muhammed-emin-eser/desk/apps/fetch_ketab/sahiha/sahihah_copy.txt",
)
