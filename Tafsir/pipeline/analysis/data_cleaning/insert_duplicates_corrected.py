import sqlite3
from pathlib import Path

from Tafsir.config import paths as cfg

# Pfade definieren
ann_path = cfg.ANNOTATED_DIR / f"{cfg.DEFAULT_TAFSIR}_annotated.sqlite3"
# Workaround databases live alongside cleaning outputs
workaround_base = cfg.PROJECT_ROOT / "pipeline" / "gemini_gui" / "analysis" / "data_cleaning_out"
corr_path = workaround_base / "duplicate_rows_corrected.sqlite3"
dup_path = workaround_base / "duplicate_rows.sqlite3"

table_name = "tafsir_analysis_katheer"


def sync_databases():
    try:
        # 1. Verbindung zur Haupt-DB (ann) herstellen
        ann_conn = sqlite3.connect(ann_path)
        ann_cursor = ann_conn.cursor()

        # 2. IDs aus der Duplikat-DB (dup) holen, die gelöscht werden sollen
        dup_conn = sqlite3.connect(dup_path)
        dup_cursor = dup_conn.cursor()
        dup_cursor.execute(f"SELECT DISTINCT id FROM {table_name}")
        ids_to_delete = [row[0] for row in dup_cursor.fetchall()]
        dup_conn.close()

        if ids_to_delete:
            # Löschen der betroffenen IDs aus ann
            placeholders = ", ".join(["?" for _ in ids_to_delete])
            ann_cursor.execute(
                f"DELETE FROM {table_name} WHERE id IN ({placeholders})", ids_to_delete
            )
            print(
                f"Gelöscht: {ann_cursor.rowcount} Zeilen aus der Hauptdatenbank (ann)."
            )
        else:
            print("Keine IDs zum Löschen in der Duplikat-DB gefunden.")

        # 3. Korrigierte Zeilen aus corr extrahieren
        corr_conn = sqlite3.connect(corr_path)
        corr_cursor = corr_conn.cursor()
        corr_cursor.execute(f"SELECT * FROM {table_name}")
        corrected_rows = corr_cursor.fetchall()

        # Spaltennamen für das Einfügen holen
        corr_cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [info[1] for info in corr_cursor.fetchall()]
        corr_conn.close()

        if corrected_rows:
            # Korrigierte Zeilen in ann einfügen
            placeholders = ", ".join(["?" for _ in columns])
            column_names = ", ".join(columns)
            ann_cursor.executemany(
                f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})",
                corrected_rows,
            )
            print(
                f"Eingefügt: {len(corrected_rows)} korrigierte Zeilen in die Hauptdatenbank (ann)."
            )
        else:
            print("Keine korrigierten Zeilen in der Korrektur-DB gefunden.")

        # Änderungen speichern
        ann_conn.commit()
        ann_conn.close()
        print("Synchronisierung erfolgreich abgeschlossen.")

    except sqlite3.Error as e:
        print(f"Datenbankfehler: {e}")
    except Exception as e:
        print(f"Fehler: {e}")


if __name__ == "__main__":
    sync_databases()
