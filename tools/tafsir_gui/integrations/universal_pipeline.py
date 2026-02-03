from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

from loguru import logger
from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    MetaData,
    Text,
    create_engine,
    text,
)
from sqlalchemy.engine import Engine

from ..core.artifacts import ArtifactStore
from ..core.guards import evaluate_guard
from ..core.rules_engine import RuleEngine
from ..integrations.gemini import GeminiClient
from ..utils import db as db_utils
from ..utils import file_detect
from Tafsir.pipeline.gemini_gui.PROMPT_PREFIX import PROMPT_PREFIX


def _sample_segments(path: Path, limit: int = 5) -> List[str]:
    kind = file_detect.detect_kind(path)
    if kind == "pdf":
        raw = file_detect.sample_pdf(path, max_pages=limit)
        return [s.strip() for s in raw.split("\n\n") if s.strip()][:limit]
    if kind == "csv":
        sample = file_detect.sample_csv(path, max_rows=limit)
        return [sample]
    if kind == "sqlite":
        sample = file_detect.sample_sqlite(path, max_rows=limit)
        return [sample]
    text = file_detect.sample_text(path, max_chars=2000)
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    return parts[:limit]


def infer_blueprint(
    client: GeminiClient, samples: List[str]
) -> Tuple[Dict, str, Dict, Dict, Dict]:
    prompt = (
        "You are a data architect and pipeline engineer for the Tafsir project. Analyze the samples "
        "and infer a portable schema plus validation/repair strategy that fits the current architecture:\n"
        "- Data enters as raw excerpts, is normalized against a shared Arabic normalization routine, "
        "and is stored in SQLite tables under the `annotated` directory.\n"
        "- The legacy pipeline builds `tafsir_analysis_*` tables with section, block, and chunk tiers, "
        "always keeping the source ID stable and storing normalized XML alongside the original.\n"
        "- Guards evaluate token coverage/ngram overlap before regeneration, and diagnostics run through predefined rules.\n"
        "- We will persist the inferred schema, rules, guards, repair policy, and prompt into artifacts, "
        "build the tables, insert the generated rows, and fire the RuleEngine to validate every entry.\n"
        "Respond with JSON containing keys `schema`, `validation_rules`, `guards`, `repair_policy`, `prompt`.\n\n"
        "Schema JSON must describe tables[{name, columns[{name,type,nullable,default}], primary_key[list], "
        "indexes[list?], relationships[list?]}]. Types should use sqlite types (TEXT, INTEGER, REAL).\n"
        "validation_rules: list of rule objects (type, table, column, ...).\n"
        "guards: thresholds {token_coverage, ngram_overlap, length_ratio, ngram_n} using the exact legacy logic "
        "from `Tafsir.pipeline.gemini_common.evaluate_guard`.\n"
        "repair_policy: map of severity -> action (regenerate|align|diagnose|skip|retry).\n"
        "prompt: instruction text for generating structured rows from raw text, following the same normalization and XML rigor.\n\n"
        "Explain how you will use this output in the automated pipeline: how the schema maps to the legacy tiered section/block/chunk concept, "
        "which guard thresholds trigger each repair action, and how RuleEngine validation keeps annotations aligned.\n\n"
        "Legacy prompt architecture and tag dictionary for reference:\n```\n"
        f"{PROMPT_PREFIX}\n"
        "```\n"
        "The XML tags (columns) available are defined in `Tafsir/pipeline/gemini_gui/TAGS.py` and correspond to the same columns stored in our tables.\n\n"
        "Samples:\n" + "\n---\n".join(samples)
    )
    response = client.generate(prompt, use_cache=False)
    data = json.loads(response)
    return (
        data.get("schema", {}),
        data.get("prompt", ""),
        data.get("validation_rules", []),
        data.get("repair_policy", {}),
        data.get("guards", {}),
    )


def build_models(schema: Dict, engine: Engine) -> None:
    metadata = MetaData()
    for table in schema.get("tables", []):
        cols = []
        pk = table.get("primary_key") or []
        for col in table.get("columns", []):
            col_type = col.get("type", "TEXT").upper()
            if col_type in {"INTEGER", "INT"}:
                sa_type = Integer
            elif col_type in {"REAL", "FLOAT", "DOUBLE"}:
                sa_type = String if col.get("length") else Text
            else:
                sa_type = Text
            cols.append(
                Column(
                    col["name"],
                    sa_type,
                    nullable=col.get("nullable", True),
                    primary_key=col["name"] in pk,
                )
            )
        Table(table["name"], metadata, *cols)
    metadata.create_all(engine)


def generate_records(
    client: GeminiClient, prompt: str, segments: List[str]
) -> List[Dict]:
    payload = (
        "Use the following prompt to convert each segment into JSON rows. "
        "Return a JSON array of row objects.\n\nPrompt:\n"
        f"{prompt}\n\nSegments:\n" + "\n---\n".join(segments)
    )
    response = client.generate(payload, use_cache=False)
    data = json.loads(response)
    return data if isinstance(data, list) else []


def insert_records(engine: Engine, table_name: str, rows: List[Dict]) -> None:
    if not rows:
        return
    keys = rows[0].keys()
    cols = ", ".join(keys)
    placeholders = ", ".join(f":{k}" for k in keys)
    stmt = f"INSERT OR REPLACE INTO {table_name} ({cols}) VALUES ({placeholders})"
    with engine.begin() as conn:
        conn.execute(
            text(stmt),
            rows,
        )


def run_universal_pipeline(
    *,
    input_path: Path,
    project_root: Path,
    api_key: str,
    cache_name: str | None,
    model_id: str,
) -> Dict[str, Path]:
    artifacts = ArtifactStore(project_root)
    client = GeminiClient(api_key=api_key, cache_name=cache_name, model_id=model_id)
    samples = _sample_segments(input_path)
    schema, prompt, rules, policy, guards = infer_blueprint(client, samples)
    schema_path = artifacts.save_json("schema", schema)
    rules_path = artifacts.save_json("validation_rules", rules)
    policy_path = artifacts.save_json("repair_policy", policy)
    guards_path = artifacts.save_json("guards", guards)
    prompt_path = artifacts.save_text("prompt", prompt)

    db_path = project_root / "annotated" / f"{project_root.name}_universal.sqlite3"
    engine = db_utils.create_sqlite_engine(db_path)
    build_models(schema, engine)

    segments = _sample_segments(input_path, limit=25)
    records = generate_records(client, prompt, segments)
    default_table = schema.get("tables", [{}])[0].get("name", "records")
    insert_records(engine, default_table, records)

    report = RuleEngine(engine).run_rules(rules)
    validation_report = [
        {
            "rule": r.rule,
            "ok": r.ok,
            "offending_ids": r.offending_ids,
            "message": r.message,
        }
        for r in report
    ]
    report_path = artifacts.save_json(
        "validation_report", {"results": validation_report}
    )

    return {
        "schema": schema_path,
        "rules": rules_path,
        "policy": policy_path,
        "guards": guards_path,
        "prompt": prompt_path,
        "validation_report": report_path,
        "db": db_path,
    }


__all__ = ["run_universal_pipeline"]
