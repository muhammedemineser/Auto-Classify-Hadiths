from pathlib import Path

books = ["Tirmizi", "Nesai", "Muslim", "Bukhari", "IbnMaja", "AbuDaud"]
i = 0
for book in books:

    folder = Path(
        f"/home/muhammed-emin-eser/desk/apps/classify/Leeds_KSU-Hadith-Corpus/{book}"
    )

    files = sorted(
        folder.glob("Chapter*.csv"), key=lambda p: int(p.stem.replace("Chapter", ""))
    )

    for f in files:
        i += 1
        with open(f, "r", encoding="utf-8") as g:
            lines = g.readlines()
            with open(
                f"/home/muhammed-emin-eser/desk/apps/classify/Hadith/Sorted/{book}/Chapter{i}.csv",
                "w",
                encoding="utf-8",
            ) as f:
                f.write(" ".join(lines))
    i = 0
