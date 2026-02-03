import html
import json
import os
import re

TAG_RE = re.compile(r"<[^>]+>")


def strip_html(value):
    """Remove HTML tags from strings and recursively clean lists/dicts."""
    if isinstance(value, str):
        cleaned = TAG_RE.sub("", value)
        return html.unescape(cleaned).strip()
    if isinstance(value, list):
        return [strip_html(item) for item in value]
    if isinstance(value, dict):
        return {key: strip_html(val) for key, val in value.items()}
    return value


def merge_tafsir_jsons(input_folder, output_file):
    all_blocks = []
    total_matched = 0
    total_blocks_count = 0

    # Alle JSON-Dateien im Ordner finden (außer der Output-Datei selbst)
    files = [
        f
        for f in os.listdir(input_folder)
        if f.endswith(".json") and f != os.path.basename(output_file)
    ]

    print(f"Verarbeite {len(files)} Dateien...")

    for file_name in files:
        # Extrahiere den Namen (z.B. "katheer" aus "gefiltert_katheer.json" oder "katheer.json")
        source_name = file_name.replace("gefiltert_", "").replace(".json", "")

        file_path = os.path.join(input_folder, file_name)
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)

                # Prüfen ob Liste oder Dictionary
                content = data[0] if isinstance(data, list) else data

                if "blocks" in content:
                    for block in content["blocks"]:
                        # HIER wird die Quelle hinzugefügt
                        cleaned_block = strip_html(block)
                        cleaned_block["source"] = source_name
                        all_blocks.append(cleaned_block)

                if "meta" in content:
                    total_matched += content["meta"].get("matched_blocks", 0)
                    total_blocks_count += content["meta"].get("total_blocks", 0)

            except Exception as e:
                print(f"Fehler beim Lesen von {file_name}: {e}")

    # Nach block_id sortieren
    all_blocks.sort(key=lambda x: x.get("block_id", 0))

    # Finale Struktur
    combined_result = {
        "meta": {
            "description": "Merged and Sorted Tafsir Data with Sources",
            "total_files_merged": len(files),
            "total_blocks_sum": total_blocks_count,
            "total_matched_sum": total_matched,
        },
        "blocks": all_blocks,
    }

    # Speichern
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(combined_result, f, ensure_ascii=False, indent=2)

    print("---")
    print(f"Erfolgreich gespeichert: {output_file}")
    print(f"Blöcke insgesamt: {len(all_blocks)}")


if __name__ == "__main__":
    DATA_FOLDER = "./data"
    OUTPUT_NAME = "./data/tafsir_merged_sorted.json"

    if os.path.exists(DATA_FOLDER):
        merge_tafsir_jsons(DATA_FOLDER, OUTPUT_NAME)
    else:
        print(f"Ordner {DATA_FOLDER} nicht gefunden.")
