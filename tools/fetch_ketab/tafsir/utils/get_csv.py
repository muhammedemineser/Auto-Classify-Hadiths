import pandas as pd
import glob
import os


def extract_matn_to_txt(input_folder, output_file):
    # Alle .csv Dateien im Ordner finden
    csv_files = glob.glob(os.path.join(input_folder, "*.csv"))

    if not csv_files:
        print(f"Keine CSV-Dateien im Ordner '{input_folder}' gefunden.")
        return

    print(f"{len(csv_files)} Dateien gefunden. Starte Extraktion...")

    with open(output_file, "w", encoding="utf-8") as f_out:
        for file_path in csv_files:
            try:
                # CSV laden (sep=None lässt pandas das Trennzeichen automatisch raten)
                df = pd.read_csv(file_path, encoding="utf-8", sep=None, engine="python")

                # Prüfen, ob die Spalte 'Arabic_Matn' existiert
                if "Arabic_Matn" in df.columns:
                    # Alle Einträge der Spalte extrahieren, leere Zeilen entfernen
                    matn_list = df["Arabic_Matn"].dropna().astype(str).tolist()

                    for line in matn_list:
                        # Bereinigung: Zeilenumbrüche innerhalb des Textes entfernen
                        clean_line = line.replace("\n", " ").replace("\r", "").strip()
                        if clean_line:
                            f_out.write(clean_line + "\n")
                else:
                    print(
                        f"Warnung: '{os.path.basename(file_path)}' hat keine Spalte 'Arabic_Matn'."
                    )

            except Exception as e:
                print(f"Fehler beim Lesen von {os.path.basename(file_path)}: {e}")

    print(f"Fertig! Alle Matn wurden in '{output_file}' gespeichert.")


# --- KONFIGURATION ---
ORDNER_PFAD = "/home/muhammed-emin-eser/desk/apps/fetch_ketab/sahihah/LK-Hadith-Corpus/Muslim"  # Ersetze dies durch deinen Pfad
AUSGABE_DATEI = "/home/muhammed-emin-eser/desk/apps/fetch_ketab/sahihah/muslim.txt"

extract_matn_to_txt(ORDNER_PFAD, AUSGABE_DATEI)
