import sqlite3
import re
from pathlib import Path
from collections import Counter

from Tafsir.config import paths as cfg

DB_PATH = cfg.LOGS_DIR / "analysis_results.sqlite3"

LOG_PATH = cfg.LOGS_DIR / "run.log"

ANALYSIS_TABLE = "run_results"
LOG_TABLE = "run_log_events"

START_MARKER = "Warte auf Antwort von Gemini..."
END_MARKER = "Antwort gespeichert. Nächster Durchgang..."


def normalize(line: str) -> str:
    return line.strip()


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Drop + create log table
    cur.execute(f"DROP TABLE IF EXISTS {LOG_TABLE}")
    cur.execute(
        f"""
        CREATE TABLE {LOG_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id INTEGER NOT NULL,
            event TEXT NOT NULL,
            occurrences INTEGER NOT NULL,
            FOREIGN KEY (analysis_id)
                REFERENCES {ANALYSIS_TABLE}(id)
        )
        """
    )

    log_lines = [normalize(l) for l in LOG_PATH.read_text().splitlines() if l.strip()]

    analysis_id = 0
    buffer = []
    end_count = 0
    inside = False

    for line in log_lines:
        if line == START_MARKER and not inside:
            analysis_id += 1
            buffer = []
            end_count = 0
            inside = True
            continue

        if not inside:
            continue

        buffer.append(line)

        if line == END_MARKER:
            end_count += 1
            if end_count == 2:
                counts = Counter(buffer)
                for event, occ in counts.items():
                    cur.execute(
                        f"""
                        INSERT INTO {LOG_TABLE}
                        (analysis_id, event, occurrences)
                        VALUES (?, ?, ?)
                        """,
                        (analysis_id, event, occ),
                    )
                inside = False
                buffer = []
                end_count = 0

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
