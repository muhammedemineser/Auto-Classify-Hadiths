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
cursor_out.execute(f"CREATE TABLE IF NOT EXISTS most_frequent (row_id INTEGER, filled_cols INTEGER, frequency_rank INTEGER, {all_cols});")


cursor.execute("SELECT * FROM tafsir_analysis_katheer;")
counts = {}
for row in cursor.fetchall():
    row_id = row[0]
    if row_id in counts:  
        continue
    filled = sum(1 for val in row[1:] if val is not None)
    counts[row_id] = filled


sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
print(sorted_counts)
max_prints = 250
    
for row_id, count in (sorted_counts): 
    conn_out.execute(f"INSERT INTO most_frequent (row_id) VALUES (?);", (row_id,))
    max_prints -= 1
    for col in all_cols.replace("VARCHARS", "").split(", "):
        row = cursor.fetchone()
        value = conn.execute(f"SELECT {col} FROM tafsir_analysis_katheer WHERE id = {row_id};").fetchone()
        conn_out.execute(
            f"""
            UPDATE most_frequent 
            SET filled_cols= ? , {col}=?, frequency_rank=?
            WHERE row_id={row_id};""",
            (count,value[0] if value else None, sorted_counts.index((row_id, count)) + 1)
        )
    print(f"Row ID: {row_id}, Count: {count}")
    if max_prints == 0:
        conn_out.commit()
        break