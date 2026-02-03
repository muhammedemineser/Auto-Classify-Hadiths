input_path = "/home/muhammed-emin-eser/desk/apps/fetch_ketab/tafsir/tafsir_books/tafsir_p_tags.txt"
output_path = (
    "/home/muhammed-emin-eser/desk/apps/fetch_ketab/sahihah/sahihah_subset.txt"
)

with open(input_path, "r", encoding="utf-8") as f_in:
    # Liest die ersten 10 Zeilen in eine Liste
    subset = [next(f_in) for _ in range(10)]

with open(output_path, "w", encoding="utf-8") as f_out:
    # Schreibt die Liste in die neue Datei
    f_out.writelines(subset)

print(f"Teilmenge (10 Zeilen) wurde in {output_path} gespeichert.")
