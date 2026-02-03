import re


def check_hadith_sequence(file_path):
    expected_nr = None
    missing_count = 0
    total_found = 0

    print(f"--- Starte Prüfung für: {file_path} ---")

    with open(file_path, "r", encoding="utf-8") as f:
        for line_nr, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            # Wir suchen NUR nach Zeilen, die mit einer Nummer beginnen
            # Wichtig: Das Skript ignoriert jetzt alle Zeilen dazwischen!
            match = re.match(r"\b(\d+)\s*", line)

            if match:
                current_nr = int(match.group(1))
                total_found += 1

                # Erster Fund setzt den Startpunkt
                if expected_nr is None:
                    expected_nr = current_nr
                    print(f"▶ Start bei Hadith Nr. {current_nr}")

                # Nur wenn wir eine Nummer finden, prüfen wir die Sequenz
                if current_nr != expected_nr:
                    # Falls die gefundene Nummer kleiner ist als erwartet (Doppelung/Fehlsortierung)
                    if current_nr < expected_nr:
                        print(
                            f"🔄 DOPPELUNG/RÜCKSPRUNG! Zeile {line_nr}: Erwartet {expected_nr}, aber gefunden: {current_nr}"
                        )
                    else:
                        print(
                            f"⚠️ LÜCKE GEFUNDEN! Zeile {line_nr}: Erwartet {expected_nr}, aber gefunden: {current_nr}"
                        )
                        missing_count += current_nr - expected_nr

                    # Die neue Erwartung ist immer current_nr + 1
                    expected_nr = current_nr + 1
                else:
                    # Sequenz ist korrekt, bereite auf den nächsten Fund vor
                    expected_nr += 1

    print("-" * 40)
    print(f"✅ Prüfung abgeschlossen.")
    print(f"Gesamtanzahl gefundener Hadithe am Zeilenanfang: {total_found}")

    if missing_count == 0:
        print("🎉 Perfekt! Alle gefundenen Hadithe sind in der richtigen Reihenfolge.")
    else:
        print(f"❌ Es fehlen insgesamt ca. {missing_count} Nummern in der Sequenz.")


# Pfad anpassen
check_hadith_sequence(
    "/home/muhammed-emin-eser/desk/apps/fetch_ketab/sahihah/sahihah_komplett.txt"
)
