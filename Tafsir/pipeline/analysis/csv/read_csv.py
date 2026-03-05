import sqlite3
from pathlib import Path

import pandas as pd

CSV_ROOT = Path(".")

con = sqlite3.connect("data.sqlite3")
for csv_path in sorted(CSV_ROOT.glob("*.csv")):
    df = pd.read_csv(csv_path)
    table_name = csv_path.stem.replace("-", "_")
    df.to_sql(table_name, con, if_exists="replace", index=False)
con.close()