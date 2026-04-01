from difflib import SequenceMatcher
cimport numpy as np
import numpy as np
from ranking import utils, config
from pathlib import Path
from math import factorial
import argparse
import json
import evaluate

BASE_DIR = Path(__file__).resolve().parent


def _pos_weight(str pos_tag):
    tag = (pos_tag or "").lower()
    return config.POS_WEIGHTS.get(tag, 1.0)


def _parse_pos(pos_value):
    if pos_value is None:
        raise ValueError("POS value cannot be None.")
    if isinstance(pos_value, (list, tuple)):
        return [str(x) for x in pos_value]
    if isinstance(pos_value, str) and pos_value.strip():
        try:
            parsed = json.loads(pos_value)
        except json.JSONDecodeError as exc:
            raise ValueError("POS must be stored as a JSON array string.") from exc
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
        raise ValueError("POS JSON must decode to an array.")
    raise TypeError(
        "Unsupported POS payload type. Expected JSON array string or list/tuple."
    )


def _dynamic_bleu_weights(int max_order, reference_pos):
    if reference_pos is None:
        raise ValueError(
            "reference_pos is required. Compute POS once during initialization and pass it to f1()."
        )
    pos_tags = _parse_pos(reference_pos)
    if not pos_tags:
        raise ValueError(
            "reference_pos is empty. POS must be precomputed in initialization stage."
        )

    token_weights = [_pos_weight(tag) for tag in pos_tags] or [1.0]
    avg_weight = float(sum(token_weights) / len(token_weights))
    order_scores = [
        (avg_weight**n) / np.sqrt(float(n)) for n in range(1, max_order + 1)
    ]
    total = float(sum(order_scores))
    return [float(x / total) for x in order_scores]


def f1(reference, candidate, wheights=None, int max_order=2, reference_pos=None):
    bleu_metric = evaluate.load("bleu")
    rouge_metric = evaluate.load("rouge")

    if wheights is None:
        wheights = _dynamic_bleu_weights(
            max_order=max_order,
            reference_pos=reference_pos,
        )
    if len(wheights) != max_order:
        raise ValueError(f"Length of weights must match max_order ({max_order}).")

    reference_list = reference if isinstance(reference, list) else [reference]
    candidate_list = candidate if isinstance(candidate, list) else [candidate]

    bleu_results = bleu_metric.compute(
        predictions=candidate_list,
        references=reference_list,
        max_order=max_order,
        weights=wheights,
    )
    rouge_results = rouge_metric.compute(
        predictions=candidate_list, references=reference_list
    )

    P = bleu_results["bleu"]
    R = rouge_results["rougeL"]
    beta = 0.7

    denom = (beta**2 * P + R) or 1e-12
    f1_score = (1 + beta**2) * (P * R) / denom
    return {"bleu": P, "rougeL": R, "f1": f1_score, "weights": wheights}

def diff_to_matrix(str ref, str cand):
    cdef list vec1_ids = []
    cdef list vec1_lens = []
    cdef list vec2_ids = []
    cdef list vec2_lens = []
    cdef object list_e = None
    cdef object list_list = None
    cdef list list_m = []
    cdef list minus = ["replace", "delete", "insert"]
    cdef str plus = "equal"

    for list_list in SequenceMatcher(None, ref, cand).get_grouped_opcodes():
        for list_e in list_list:
            list_m = list(list_e)
            if (
                (list_m[2] - list_m[1]) < 3
                and (list_m[4] - list_m[3]) < 3
                and ref[list_m[1] : list_m[1] + list_m[2]] not in ref.strip().split()
                and cand[list_m[3] : list_m[3] + (list_m[4])]
                not in cand.strip().split()
            ):
                continue
            if list_m[0] == plus:
                list_m[0] = 1
            elif list_m[0] in minus:
                list_m[0] = -1
            elif list_m != []:
                raise ValueError(f"Unexpected tag: {list_m[0]}")
            try:
                _1_ids, _1_lens = utils.char_idx_to_token_idx(
                    ref, [e for e in range(list_m[1], list_m[2] + 1)]
                )
                _2_ids, _2_lens = utils.char_idx_to_token_idx(
                    cand, [e for e in range(list_m[3], list_m[4] + 1)]
                )
                vec1_ids += _1_ids
                vec1_lens += [l * list_m[0] for l in _1_lens]
                vec2_ids += _2_ids
                vec2_lens += [l * list_m[0] for l in _2_lens]
            except IndexError:
                pass

    if vec1_ids == []:
        return (None,) * 4
    return vec1_ids, vec1_lens, vec2_ids, vec2_lens


def main():
    parser = argparse.ArgumentParser(description="Sequence matcher tool")
    parser.add_argument("-db","--db-path", default=str(BASE_DIR / "Data"))
    parser.add_argument("--table", default="text")
    parser.add_argument("--text-col", default="text")
    parser.add_argument("--normalized-col", default="text")
    parser.add_argument("--id-col", default="id")
    parser.add_argument(
        "-txt","--hadith-txt",
        default=str(
            BASE_DIR / "Data" / "Sahihah" / "sahihah_hadith_extracted_in_sittah.txt"
        ),
    )
    parser.add_argument("--current-db", default="diff_test2.db")
    args = parser.parse_args()

    config.db_path = args.db_path
    config.table = args.table
    config.text_col = args.text_col
    config.normalized_col = args.normalized_col
    config.id_col = args.id_col
    config.hadith_txt = args.hadith_txt

    db_txt = utils.get_txt_from_db(current_db=args.current_db, config=config)
    cand_txt, cand_meta = utils.get_cand_txt()

    cdef int i = 0
    cdef np.ndarray[np.float64_t, ndim=1] pos_matrix_1
    cdef np.ndarray[np.float64_t, ndim=1] pos_matrix_2
    cdef np.ndarray[np.float64_t, ndim=1] power_v1
    cdef np.ndarray[np.float64_t, ndim=1] power_v2
    cdef np.ndarray[np.float64_t, ndim=1] pos
    cdef np.ndarray[np.float64_t, ndim=1] neg
    cdef float percentage = 0.0
    cdef float final_score = 0.0
    cdef dict val = {}
    cdef dict f1_result = {}
    for i, (key, val) in enumerate(cand_meta.items()):
        vec1_ids, vec1_lens, vec2_ids, vec2_lens = diff_to_matrix(
            val["normalized"], db_txt[i][0]
        )
        try:
            if vec1_ids is None:
                print(f"ID:{i+1} 100.00 % Übereinstimmung")
                continue
        except ValueError:
            pass
        pos_matrix_1 = np.vectorize(lambda i: config.POS_WEIGHTS.get(val["pos"][int(i)]))(
            np.array([v for v in vec1_ids],dtype=np.int16)
        )

        pos_matrix_2 = np.vectorize(lambda i: config.POS_WEIGHTS.get(val["pos"][int(i)]))(
            np.array([v for v in vec1_ids],dtype=np.int16)
        )

        power_v1 = np.array(vec1_lens,dtype=np.int64) * pos_matrix_1[vec1_ids]
        power_v2 = np.array(vec2_lens,dtype=np.int64) * pos_matrix_2[vec2_ids]

        pos = np.where(power_v1 > 0, power_v1, 0)
        pos = np.append(pos, np.where(power_v2 > 0, power_v2, 0))
        neg = np.where(power_v1 < 0, power_v1, 0)
        neg = np.append(neg, np.where(power_v2 < 0, power_v2, 0))

        percentage = np.sum(pos) / (np.sum(pos) + (np.sum(neg) * (-1)))
        f1_result = f1(
            reference=val["normalized"],
            candidate=db_txt[i][0],
            reference_pos=val["pos"],
        )
        final_score = percentage * f1_result["f1"]

        print(f"ID:{i+1} {final_score*100:.2f}", "% Übereinstimmung")


if __name__ == "__main__":
    main()
