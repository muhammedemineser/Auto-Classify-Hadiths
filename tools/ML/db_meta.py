from sqlalchemy import create_engine, inspect

engine = create_engine("sqlite:///quran.db")
inspector = inspect(engine)

# Alle Tabellennamen abrufen
for table_name in inspector.get_table_names():
    print(f"\nTable: {table_name}")

    # Spalten, Typen und Keys
    for column in inspector.get_columns(table_name):
        pk = " [PK]" if column.get("primary_key") else ""
        print(f"  - {column['name']}: {column['type']}{pk}")

    # Foreign Keys
    for fk in inspector.get_foreign_keys(table_name):
        print(
            f"  -> FK: {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}"
        )
