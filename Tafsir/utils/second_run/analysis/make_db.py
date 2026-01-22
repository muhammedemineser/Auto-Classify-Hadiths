import sqlite3
from pathlib import Path

# ---------- Ziel-DB ----------
OUT_DB = Path(
    "/home/muhammed-emin-eser/desk/apps/classify/Tafsir/logs/analysis_results.sqlite3"
)
OUT_TABLE = "analysis_window_stats"
# ----------------------------


def init_db(conn):
    cur = conn.cursor()
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {OUT_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_id INTEGER NOT NULL,
            end_id INTEGER NOT NULL,
            created_at_start TEXT NOT NULL,
            created_at_end TEXT NOT NULL,
            delta_seconds REAL NOT NULL,
            total_words INTEGER NOT NULL,
            words_per_second REAL NOT NULL,
            seconds_per_word REAL NOT NULL
        )
        """
    )
    conn.commit()


def insert_results(conn, results):
    cur = conn.cursor()
    cur.executemany(
        f"""
        INSERT INTO {OUT_TABLE} (
            start_id,
            end_id,
            created_at_start,
            created_at_end,
            delta_seconds,
            total_words,
            words_per_second,
            seconds_per_word
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                r["start_id"],
                r["end_id"],
                r["created_at_start"],
                r["created_at_end"],
                r["delta_seconds"],
                r["total_words"],
                r["words_per_second"],
                r["seconds_per_word"],
            )
            for r in results
        ],
    )
    conn.commit()


def main(results):
    conn = sqlite3.connect(OUT_DB)
    init_db(conn)
    insert_results(conn, results)
    conn.close()


# --- Aufruf nach deiner Analyse ---
# main(results)
