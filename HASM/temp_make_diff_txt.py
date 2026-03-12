import sqlite3
from ranking import utils

conn = sqlite3.connect("/home/mo/desk/apps/classify/HASM/Data/diff_test.db")
c = conn.cursor()
text = c.execute("SELECT * FROM text")
text = text.fetchall()
print(text)
with open("diff.txt", "w") as f:
    for t in text:
        f.write(f"{t[0]} {" ".join(utils.normalize(t[1]))} \n")
        c.execute(
            "UPDATE text SET text = ? WHERE id = ?",
            (" ".join(utils.normalize(t[1])), t[0]),
        )
    conn.commit()
