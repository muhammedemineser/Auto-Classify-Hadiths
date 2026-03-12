from difflib import SequenceMatcher
import numpy as np
import sqlite3
from ranking import utils
import timeit
from pprint import pprint

conn = sqlite3.connect("/home/mo/desk/apps/classify/HASM/Data/diff_test.db")
c = conn.cursor()
c.execute("SELECT text FROM version_a")
rows1 = [row[0] for row in c.fetchall()]

c.execute("SELECT text FROM version_b")
rows2 = [row[0] for row in c.fetchall()]


def diff_to_matrix(ref, cand):
    matrix = []

    for list_list in SequenceMatcher(None, ref, cand).get_grouped_opcodes():
        for list_e in list_list:
            list_e = list(list_e)
            if list_e[0] == "equal":
                list_e[0] = 1
            elif list_e[0] in ["replace", "delete", "insert"]:
                list_e[0] = -1
            elif list_e != []:
                raise ValueError(f"Unexpected tag: {list_e[0]}")
            matrix.append(list_e)
    arr = np.array(matrix, dtype=np.int16)
    arr = arr.reshape(-1, 5)

    return arr


total_time = 0
for i, row in enumerate(rows1):
    matrix = diff_to_matrix(row, rows2[i])
    vec1 = np.array(
        [[(arr[:, 2] - arr[:, 1]) * arr[:, 0]] for arr in [matrix]],
        dtype=np.int16,
    )
    vec2 = np.array(
        [[(arr[:, 4] - matrix[:, 3]) * arr[:, 0]] for arr in [matrix]],
        dtype=np.int16,
    )
    dot = vec1 + vec2
    positive = dot[dot > 0].sum()
    negative = dot[dot < 0].sum()
    percentage = positive / (positive + (negative * (-1)))
    print(matrix)
    print(vec1, vec2)
    print(dot)
    print(positive)
    print(negative)
    if percentage != percentage:
        percentage = 100

    print(f"ID:{i+1} {percentage*100:.2f}", "% Übereinstimmung")

    total_time += (
        timeit.timeit(lambda: diff_to_matrix(row, rows2[i]), number=1000) / 1000
    )


print(
    f"{'PERFORMANCE':^20} \n",
    f"{total_time:.4f} s",
)
