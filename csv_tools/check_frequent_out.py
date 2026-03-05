import sqlite3
db_path = "/app/Tafsir/tafsir_books_annotated/katheer_annotated.sqlite3"
out_db_path = "/app/csv_tools/FINAL_CSVS/katheer_annotated_most_frequent.sqlite3"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(tafsir_analysis_katheer);")
columns = cursor.fetchall()
names = [col[1] for col in columns]

conn_out = sqlite3.connect(out_db_path)
cursor_out = conn_out.cursor()
all_cols = " VARCHARS, ".join(names)
cursor_out.execute(f"CREATE TABLE IF NOT EXISTS most_frequent (row_id INTEGER, count INTEGER, frequency_rank INTEGER, {all_cols});")


cursor_out.execute("SELECT * FROM most_frequent;")
counts = {}
for row in cursor_out.fetchall():
    row_id = row[0]
    filled = sum(1 for val in row[4:] if val is not None)  # row_id, count, frequency_rank, id überspringen
    counts[row_id] = filled

sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
print(sorted_counts)  