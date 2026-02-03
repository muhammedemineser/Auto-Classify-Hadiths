import re


def sync_missing_hadiths(source_file, target_file, output_file):
    # 1. Extrahiere alle Hadith-Blöcke aus der Quelldatei
    source_data = {}
    print(f"📖 Lese Quelldatei: {source_file}")

    with open(source_file, "r", encoding="utf-8") as f:
        current_content = f.read()
        # Wir finden alle "Nummer -" Muster am Zeilenanfang (^) oder nach einem Zeilenumbruch
        # Das Regex nutzt ein Lookahead, um bis zum nächsten "Zahl -" zu lesen
        matches = re.finditer(
            r"(?:^|\n)(\d+)\s*-(.*?)(?=\n\d+\s*-|$)", current_content, re.DOTALL
        )
        for m in matches:
            nr = int(m.group(1))
            content = m.group(2).strip()
            source_data[nr] = content

    # 2. Zieldatei einlesen
    print(f"📖 Lese Zieldatei: {target_file}")
    with open(target_file, "r", encoding="utf-8") as f:
        target_lines = [line.strip() for line in f if line.strip()]

    final_output = []
    last_valid_nr = 0  # Sorgt dafür, dass Zahlen immer größer sein müssen

    # 3. Zieldatei Zeile für Zeile durchgehen und Lücken füllen
    print("🛠 Integriere fehlende Zeilen...")

    for i in range(len(target_lines)):
        current_line = target_lines[i]
        final_output.append(current_line)

        # Prüfe, ob die aktuelle Zeile mit einer Hadith-Nummer beginnt
        # Wir nutzen ^(\d+), damit Seitenzahlen mitten im Text ignoriert werden
        match_curr = re.search(r"^(\d+)\s*-", current_line)

        if match_curr:
            curr_nr = int(match_curr.group(1))

            # MONOTONIE-CHECK: Nur wenn die Zahl größer als die letzte ist
            if curr_nr > last_valid_nr:
                last_valid_nr = curr_nr

                # Suche in den folgenden Zeilen nach dem nächsten validen Anker
                next_nr = None
                for j in range(i + 1, len(target_lines)):
                    match_next = re.search(r"^(\d+)\s*-", target_lines[j])
                    if match_next:
                        potential_next = int(match_next.group(1))
                        # Nur akzeptieren, wenn sie größer ist (Seitenzahlen-Schutz)
                        if potential_next > curr_nr:
                            next_nr = potential_next
                            break

                # Wenn eine echte Lücke erkannt wurde
                if next_nr and next_nr > curr_nr + 1:
                    for missing_nr in range(curr_nr + 1, next_nr):
                        if missing_nr in source_data:
                            print(f"  ➕ Füge Hadith {missing_nr} nach {curr_nr} ein.")
                            # Formatierte Zeile hinzufügen
                            final_output.append(
                                f"{missing_nr}- {source_data[missing_nr]}"
                            )
                            last_valid_nr = missing_nr  # Update Tracker
                        else:
                            print(
                                f"  ⚠️ Warnung: {missing_nr} fehlt auch in der Quelldatei!"
                            )

    # 4. Speichern
    with open(output_file, "w", encoding="utf-8") as f:
        for line in final_output:
            f.write(line + "\n")

    print(f"✅ Synchronisation abgeschlossen! Datei gespeichert als: {output_file}")


# --- SETUP ---
sync_missing_hadiths(
    "/home/muhammed-emin-eser/desk/apps/fetch_ketab/sahihah_final_fixed.txt",
    "/home/muhammed-emin-eser/desk/apps/fetch_ketab/sahihah/sahihah_copy.txt",
    "sahihah_komplett.txt",
)
