from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import text
from sqlalchemy.engine import Engine


@dataclass
class RuleResult:
    rule: Dict[str, Any]
    ok: bool
    offending_ids: List[Any]
    message: str


class RuleEngine:
    def __init__(self, engine: Engine):
        self.engine = engine

    def run_rules(self, rules: List[Dict[str, Any]]) -> List[RuleResult]:
        results: List[RuleResult] = []
        for rule in rules:
            rtype = rule.get("type")
            table = rule.get("table")
            if not rtype or not table:
                continue
            try:
                if rtype == "not_null":
                    res = self._not_null(table, rule["column"])
                elif rtype == "unique":
                    res = self._unique(table, rule["column"])
                elif rtype == "regex":
                    res = self._regex(table, rule["column"], rule.get("pattern", ".*"))
                elif rtype == "range":
                    res = self._range(
                        table, rule["column"], rule.get("min"), rule.get("max")
                    )
                elif rtype == "foreign_key":
                    res = self._foreign_key(
                        table,
                        rule["column"],
                        rule["ref_table"],
                        rule["ref_column"],
                    )
                else:
                    res = RuleResult(rule, True, [], "Unknown rule type skipped.")
            except Exception as exc:  # pragma: no cover
                logger.warning("Rule failed {}: {}", rule, exc)
                res = RuleResult(rule, False, [], f"Rule error: {exc}")
            results.append(res)
        return results

    def _not_null(self, table: str, column: str) -> RuleResult:
        rows = self.engine.execute(
            text(f"SELECT rowid FROM {table} WHERE {column} IS NULL OR {column}=''")
        ).fetchall()
        ids = [r[0] for r in rows]
        return RuleResult(
            {"type": "not_null", "table": table, "column": column},
            ok=len(ids) == 0,
            offending_ids=ids,
            message="NULL/empty check",
        )

    def _unique(self, table: str, column: str) -> RuleResult:
        rows = self.engine.execute(
            text(
                f"SELECT {column}, COUNT(*) c FROM {table} "
                f"WHERE {column} IS NOT NULL GROUP BY {column} HAVING c>1"
            )
        ).fetchall()
        ids = [r[0] for r in rows]
        return RuleResult(
            {"type": "unique", "table": table, "column": column},
            ok=len(ids) == 0,
            offending_ids=ids,
            message="Uniqueness check",
        )

    def _regex(self, table: str, column: str, pattern: str) -> RuleResult:
        try:
            compiled = re.compile(pattern)
        except re.error as exc:
            return RuleResult(
                {"type": "regex", "table": table, "column": column},
                False,
                [],
                f"Invalid regex: {exc}",
            )
        rows = self.engine.execute(
            text(f"SELECT rowid, {column} FROM {table}")
        ).fetchall()
        bad = [r[0] for r in rows if r[1] is None or not compiled.search(str(r[1]))]
        return RuleResult(
            {"type": "regex", "table": table, "column": column, "pattern": pattern},
            ok=len(bad) == 0,
            offending_ids=bad,
            message="Regex pattern check",
        )

    def _range(self, table: str, column: str, min_val: Any, max_val: Any) -> RuleResult:
        clause = []
        params = {}
        if min_val is not None:
            clause.append(f"{column} < :min")
            params["min"] = min_val
        if max_val is not None:
            clause.append(f"{column} > :max")
            params["max"] = max_val
        if not clause:
            return RuleResult(
                {"type": "range", "table": table, "column": column},
                True,
                [],
                "Range not applied (no bounds).",
            )
        sql = f"SELECT rowid FROM {table} WHERE " + " OR ".join(clause)
        rows = self.engine.execute(text(sql), params).fetchall()
        ids = [r[0] for r in rows]
        return RuleResult(
            {"type": "range", "table": table, "column": column, "min": min_val, "max": max_val},
            ok=len(ids) == 0,
            offending_ids=ids,
            message="Range check",
        )

    def _foreign_key(
        self, table: str, column: str, ref_table: str, ref_column: str
    ) -> RuleResult:
        rows = self.engine.execute(
            text(
                f"SELECT t.rowid FROM {table} t "
                f"LEFT JOIN {ref_table} r ON t.{column}=r.{ref_column} "
                f"WHERE t.{column} IS NOT NULL AND r.{ref_column} IS NULL"
            )
        ).fetchall()
        ids = [r[0] for r in rows]
        return RuleResult(
            {
                "type": "foreign_key",
                "table": table,
                "column": column,
                "ref_table": ref_table,
                "ref_column": ref_column,
            },
            ok=len(ids) == 0,
            offending_ids=ids,
            message="Foreign key integrity",
        )


__all__ = ["RuleEngine", "RuleResult"]
