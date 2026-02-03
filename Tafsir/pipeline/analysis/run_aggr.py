import sqlite3
from datetime import datetime
from pathlib import Path

from Tafsir.config import paths as cfg

# ---------- Konfiguration ----------
ANALYSIS_DB = cfg.ANNOTATED_DIR / "katheer_annotated.sqlite3"
ANALYSIS_TABLE = f"tafsir_analysis_{cfg.DEFAULT_TAFSIR}"
CREATED_AT_COL = "created_at"

SOURCE_DB = cfg.BOOKS_DIR / f"{cfg.DEFAULT_TAFSIR}.sqlite3"
SOURCE_TABLE = cfg.DEFAULT_TAFSIR
SOURCE_TEXT_COL = "text"

TIME_FMT = "%Y-%m-%d %H:%M:%S"

START_ID = 0
STEP = 5

# ---------- Ziel-DB ----------
OUT_DB = cfg.LOGS_DIR / "analysis_results.sqlite3"
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


def results_to_db(results):
    conn = sqlite3.connect(OUT_DB)
    init_db(conn)
    insert_results(conn, results)
    conn.close()


# ----------------------------------


def get_analysis_points(conn):
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT id, {CREATED_AT_COL}
        FROM {ANALYSIS_TABLE}
        WHERE id >= ?
          AND id % ? = 0
        ORDER BY id
        """,
        (START_ID, STEP),
    )
    return cur.fetchall()


def get_source_texts(conn, start_id, end_id):
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT id, {SOURCE_TEXT_COL}
        FROM {SOURCE_TABLE}
        WHERE id BETWEEN ? AND ?
        ORDER BY id
        """,
        (start_id, end_id),
    )

    texts = []
    for _, text in cur.fetchall():
        if not text:
            continue

        text = " ".join(text.replace("<p>", " ").replace("</p>", " ").split())

        texts.append(text)

    return texts


def word_count(text: str) -> int:
    return len(text.split())


def main():
    analysis_conn = sqlite3.connect(ANALYSIS_DB)
    source_conn = sqlite3.connect(SOURCE_DB)

    points = get_analysis_points(analysis_conn)

    results = []

    for (id1, t1), (id2, t2) in zip(points, points[1:]):
        dt1 = datetime.strptime(t1, TIME_FMT)
        dt2 = datetime.strptime(t2, TIME_FMT)
        delta_seconds = (dt2 - dt1).total_seconds()

        start_id = id1 - (STEP - 1)
        end_id = id1

        texts = get_source_texts(source_conn, start_id, end_id)
        total_words = sum(word_count(t) for t in texts)

        if total_words == 0 or delta_seconds <= 0:
            continue

        results.append(
            {
                "start_id": start_id,
                "end_id": end_id,
                "created_at_start": t1,
                "created_at_end": t2,
                "delta_seconds": delta_seconds,
                "total_words": total_words,
                "words_per_second": total_words / delta_seconds,
                "seconds_per_word": delta_seconds / total_words,
            }
        )

    analysis_conn.close()
    source_conn.close()

    for r in results:
        print(
            f"{r['start_id']}-{r['end_id']} | "
            f"{r['created_at_start']} -> {r['created_at_end']} | "
            f"{r['delta_seconds']:.2f}s | "
            f"{r['total_words']} words | "
            f"{r['words_per_second']:.2f} w/s"
        )
    results_to_db(results)


if __name__ == "__main__":
    main()
