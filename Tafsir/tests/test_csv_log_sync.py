import json
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "output_csvs"
LOGS_DIR = REPO_ROOT / "Tafsir" / "logs"


def _log_path_for_suffix(suffix: str) -> Path:
    candidates = [
        LOGS_DIR / f"structured_logs_{suffix}.json",
        LOGS_DIR / "structured_logs.filtered.json",
        LOGS_DIR / "structured_logs_all.json",
    ]
    for cand in candidates:
        if cand.exists():
            return cand
    raise FileNotFoundError(f"No structured log file found for suffix {suffix}")


def _expected_entry(entry: dict, model_label: str) -> dict:
    guard_idxs = [i for i, g in enumerate(entry.get("guard", [])) if g.get("model_label") == model_label]
    guard = [entry["guard"][i] for i in guard_idxs]
    progress = [entry.get("progress", [])[i] for i in guard_idxs if i < len(entry.get("progress", []))]
    responses = [entry.get("responses", [])[i] for i in guard_idxs if i < len(entry.get("responses", []))]
    return {
        "progress": progress,
        "guard": guard,
        "responses": responses,
    }


def test_csv_log_entries_match_structured_logs():
    csv_files = list(OUTPUT_DIR.glob("katheer_annotated_subset_*.csv"))
    assert csv_files, "No CSV files found in output_csvs; generate them first."

    for csv_path in csv_files:
        suffix = csv_path.stem.split("_")[-1]
        log_path = _log_path_for_suffix(suffix)
        logs = json.loads(log_path.read_text(encoding="utf-8"))

        df = pd.read_csv(csv_path)
        assert "log_json" in df.columns, f"log_json column missing in {csv_path.name}"

        for _, row in df.iterrows():
            rid = str(int(row["id"]))
            assert rid in logs, f"ID {rid} missing in logs for {csv_path.name}"
            expected = _expected_entry(logs[rid], suffix)
            actual = json.loads(row["log_json"])
            assert actual == expected, (
                f"Mismatch for id {rid} in {csv_path.name}:\n"
                f"expected {expected}\nactual   {actual}"
            )
