from difflib import SequenceMatcher
import numpy as np
import sqlite3
from ranking import utils, config
import timeit
from pprint import pprint
import json
from typing import Any, Iterable, Optional
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

config.db_path = str(BASE_DIR / "Data")
config.table = "text"
config.text_col = "text"
config.normalized_col = "text"
config.id_col = "id"
config.hadith_txt = str(BASE_DIR / "Data" / "diff.txt")
config.dbs = ["diff_test.db", "diff_test2.db"]
db_txt = utils.get_txt_from_db(current_db="diff_test2.db", config=config)
cand_txt, cand_meta = utils.get_cand_txt()


def diff_to_matrix(ref: str, cand: str):
    seq_res: list = []
    pos_res: list = []

    for list_list in SequenceMatcher(None, ref, cand).get_grouped_opcodes():
        for list_e in list_list:
            list_e = list(list_e)
            if list_e[0] == "equal":
                list_e[0] = 1
            elif list_e[0] in ["replace", "delete", "insert"]:
                list_e[0] = -1
            elif list_e != []:
                raise ValueError(f"Unexpected tag: {list_e[0]}")
            vec1_indexes = list(
                set(
                    utils.char_idx_to_token_idx(
                        ref, [e for e in range(list_e[1], list_e[2] + 1)]
                    )
                )
            )
            vec2_indexes = list(
                set(
                    utils.char_idx_to_token_idx(
                        cand, [e for e in range(list_e[3], list_e[4] + 1)]
                    )
                )
            )
            seq_res.append(list_e)
            pos_res.append([vec1_indexes, vec2_indexes])
    if seq_res == []:
        return ["empty"], None
    seq_matrix = np.array(seq_res, dtype=np.int16).reshape(-1, 5)
    max_outer = max(len(x) for x in pos_res)
    max_inner = max(len(row) for x in pos_res for row in x)

    pos_matrix = np.array(
        [
            [row + [0] * (max_inner - len(row)) for row in x]
            + [[0] * max_inner] * (max_outer - len(x))
            for x in pos_res
        ],
        dtype=np.int16,
    )
    return seq_matrix, pos_matrix


def main():
    total_time = 0


for i, (key, val) in enumerate(cand_meta.items()):
    seq_matrix, _pos = diff_to_matrix(val["normalized"], db_txt[i][0])
    try:
        if seq_matrix[0] == "empty":
            print(f"ID:{i+1} 100% Übereinstimmung")
            continue
    except:
        pass
    vec1 = np.array(
        [[(arr[:, 2] - arr[:, 1]) * arr[:, 0]] for arr in [seq_matrix]],
        dtype=np.int16,
    )
    vec2 = np.array(
        [[(arr[:, 4] - seq_matrix[:, 3]) * arr[:, 0]] for arr in [seq_matrix]],
        dtype=np.int16,
    )
    pos_matrix = np.vectorize(lambda i: config.POS_WEIGHTS.get(val["pos"][i]))(_pos)
    pos1 = pos_matrix[:, 0].sum()  ## falsch
    pos2 = pos_matrix[:, 1].sum()  ## falsch
    dot_pos_v1 = pos1 * vec1
    dot_pos_v2 = pos2 * vec2
    dot_vecs = dot_pos_v1 + dot_pos_v2
    positive = dot_vecs[dot_vecs > 0].sum()
    negative = dot_vecs[dot_vecs < 0].sum()
    percentage = positive / (positive + (negative * (-1)))
    print(seq_matrix)
    print(vec1, vec2)
    print(dot_vecs)
    print(positive)
    print(negative)

    print(f"ID:{i+1} {percentage*100:.2f}", "% Übereinstimmung")

    # total_time += (
    #     timeit.timeit(lambda: diff_to_matrix(row, db_txt[i]), number=1000) / 1000
    # )

# print(
#     f"{'PERFORMANCE':^20} \n",
#     f"{total_time:.4f} s",
# )


if __name__ == "__main__":
    main()
