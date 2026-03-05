import pandas as pd
import sqlite3
from pathlib import Path

# Quelle: CSVs liegen modellweise in Unterverzeichnissen
CSV_ROOT = Path("/app/FINAL_CSVS")

# Ziel: gleiche Struktur, aber mit SQLite-Datenbanken
OUT_BASE = Path("/app/ALL_FINAL_SQLITES")
OUT_BASE.mkdir(parents=True, exist_ok=True)

# Alle Modell-Unterverzeichnisse durchlaufen
for model_dir in sorted(p for p in CSV_ROOT.iterdir() if p.is_dir()):
    out_model_dir = OUT_BASE / model_dir.name
    out_model_dir.mkdir(parents=True, exist_ok=True)

    # Jede CSV in genau diesem Unterverzeichnis
    for csv_path in sorted(model_dir.glob("*.csv")):
        sqlite_path = out_model_dir / f"{csv_path.stem}.sqlite3"
        table_name = csv_path.stem  # exakt, unverändert

        df = pd.read_csv(csv_path)

        con = sqlite3.connect(sqlite_path)
        df.to_sql(table_name, con, if_exists="fail", index=False)
        con.close()
