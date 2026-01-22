from __future__ import annotations

import hashlib
import html
import os
import re
import sqlite3
import xml.etree.ElementTree as ET
from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app_vars import (
    SURAH_NAMES,
    TAG_COLORS,
    DEPENDENT_FILTERS,
    FILTER_ALIASES,
    ABSOLUTE_FILTERS,
)

# ---------------- Configuration ----------------

ANNOTATED_DIR = Path(os.getenv("ANNOTATED_DIR", "../tafsir_books_annotated"))
SOURCE_DIR = Path(os.getenv("SOURCE_DIR", "../tafsir_books"))
DEFAULT_TAFSIR = os.getenv("DEFAULT_TAFSIR", "katheer")

# Optional explicit defaults (used when auto-discovery finds nothing)
ANNOTATED_DB_PATH = os.getenv(
    "ANNOTATED_DB", str(ANNOTATED_DIR / "katheer_annotated.sqlite3")
)
SOURCE_DB_PATH = os.getenv("SOURCE_DB", str(SOURCE_DIR / "katheer.sqlite3"))
ANNOTATED_TABLE = os.getenv("ANNOTATED_TABLE", "tafsir_analysis_katheer")
BLOCKS_TABLE = os.getenv("BLOCKS_TABLE", "tafsir_analysis_katheer_blocks")
CHUNKS_TABLE = os.getenv("CHUNKS_TABLE", "tafsir_analysis_katheer_chunks")
SOURCE_TABLE = os.getenv("SOURCE_TABLE", "katheer")


@dataclass(frozen=True)
class TafsirConfig:
    key: str
    annotated_db: str
    annotated_table: str
    blocks_table: str
    chunks_table: str
    source_db: str
    source_table: str


def discover_tafsir_configs() -> Dict[str, TafsirConfig]:
    """
    Auto-discover annotated tafsir databases and wire them to their source DBs.
    Naming convention:
      annotated DB: <name>_annotated.sqlite3
      annotated table: tafsir_analysis_<name>
      blocks table: tafsir_analysis_<name>_blocks
      chunks table: tafsir_analysis_<name>_chunks
      source DB: Tafsir/tafsir_books/<name>.sqlite3
      source table: <name>
    """
    configs: Dict[str, TafsirConfig] = {}

    if ANNOTATED_DIR.exists():
        for path in ANNOTATED_DIR.glob("*_annotated.sqlite3"):
            stem = path.stem
            if " copy" in stem.lower():
                continue  # skip backup/copy files
            if not stem.endswith("_annotated"):
                continue
            base = stem[: -len("_annotated")]
            key = base.lower()
            if not key or key in configs:
                continue
            source_db = SOURCE_DIR / f"{key}.sqlite3"
            configs[key] = TafsirConfig(
                key=key,
                annotated_db=str(path),
                annotated_table=f"tafsir_analysis_{base}",
                blocks_table=f"tafsir_analysis_{base}_blocks",
                chunks_table=f"tafsir_analysis_{base}_chunks",
                source_db=str(source_db),
                source_table=base,
            )

    if not configs:
        # Fallback to explicit env/config defaults (keeps app bootable during setup).
        fallback_key = DEFAULT_TAFSIR.lower()
        configs[fallback_key] = TafsirConfig(
            key=fallback_key,
            annotated_db=ANNOTATED_DB_PATH,
            annotated_table=ANNOTATED_TABLE,
            blocks_table=BLOCKS_TABLE,
            chunks_table=CHUNKS_TABLE,
            source_db=SOURCE_DB_PATH,
            source_table=SOURCE_TABLE,
        )

    return configs


# ---------------- Text helpers ----------------

ARABIC_DIACRITICS_RE = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
TATWEEL = "\u0640"
PUNCT_RE = re.compile(r"[^\w\s\u0600-\u06FF]")
WHITESPACE_RE = re.compile(r"\s+")
TAG_RE = re.compile(r"<[^>]+>")
STRUCTURAL_TAGS = {"tafsir_section", "tafsir_section_block", "tafsir_chunk"}


def normalize(text: str) -> str:
    text = text.replace(TATWEEL, "")
    text = ARABIC_DIACRITICS_RE.sub("", text)
    text = PUNCT_RE.sub(" ", text)
    text = WHITESPACE_RE.sub(" ", text)
    return text.strip().lower()


def strip_markup(text: str) -> str:
    return TAG_RE.sub("", text or "")


def strip_html(text: str) -> str:
    without_tags = TAG_RE.sub("", text or "")
    return WHITESPACE_RE.sub(" ", without_tags).strip()


def _parse_xml(xml: str) -> Optional[ET.Element]:
    if not xml:
        return None
    try:
        return ET.fromstring(xml)
    except ET.ParseError:
        try:
            return ET.fromstring(f"<wrapper>{xml}</wrapper>")
        except ET.ParseError:
            return None


def color_for_tag(tag: str) -> str:
    if tag in TAG_COLORS:
        return TAG_COLORS[tag]
    h = int(hashlib.sha1(tag.encode("utf-8")).hexdigest()[:6], 16) % 360
    return f"hsl({h}, 65%, 72%)"

STRUCTURE_LABELS = {
    "tafsir_section": "Section",
    "tafsir_section_block": "Block",
    "tafsir_chunk": "Chunk",
}
STRUCTURE_CLASSES = {
    "tafsir_section": "section",
    "tafsir_section_block": "block",
    "tafsir_chunk": "chunk",
}


def render_xml_text(
    xml: str,
    allowed_tags: Optional[Set[str]],
    highlight: bool,
    palette: Dict[str, str],
    structural_markers: Optional[Set[str]] = None,
) -> Tuple[str, Set[str]]:
    """
    Render XML into plain text or HTML with colored spans.
    If allowed_tags is set, only text inside those tags is emitted.
    """
    root = _parse_xml(xml)
    if root is None:
        text = strip_markup(xml)
        return (html.escape(text) if highlight else text, set())

    used_tags: Set[str] = set()

    def walk(node: ET.Element) -> str:
        tag = node.tag
        is_structural = tag in STRUCTURAL_TAGS

        filtering = allowed_tags is not None
        node_allowed = not filtering or tag in allowed_tags
        node_text = node.text or ""
        parts: List[str] = []

        # Only include direct text when node is allowed (and not purely structural while filtering).
        if node_allowed and not (filtering and is_structural):
            parts.append(html.escape(node_text) if highlight else node_text)

        for child in list(node):
            parts.append(walk(child))
            # When filtering, omit tails to avoid untagged spillover text.
            if child.tail and not filtering and node_allowed:
                parts.append(html.escape(child.tail) if highlight else child.tail)

        content = "".join(parts)

        # Structural wrappers never render their own tag.
        if is_structural:
            markers = structural_markers or set()
            marker_cls = STRUCTURE_CLASSES.get(tag)
            if tag in markers and marker_cls:
                label = STRUCTURE_LABELS.get(tag, tag)
                return (
                    f'<div class="structure-marker structure-{marker_cls}" '
                    f'data-structure="{html.escape(marker_cls)}">'
                    f'<div class="structure-chip">{html.escape(label)}</div>'
                    f"{content}</div>"
                )
            return content

        # If filtering and this tag is not allowed, skip rendering this node wrapper.
        if filtering and tag not in allowed_tags:
            return content

        used_tags.add(tag)

        if highlight:
            color = palette.get(tag, color_for_tag(tag))
            return (
                f'<span class="tag-swatch" data-tag="{html.escape(tag)}" '
                f'style="background:{color};border-color:{color}">{content}</span>'
            )
        return content

    rendered = walk(root)
    return rendered, used_tags


# ---------------- Data layer ----------------


class TafsirRepository:
    def __init__(self, cfg: TafsirConfig):
        self.cfg = cfg
        self.annotated_conn = sqlite3.connect(cfg.annotated_db, check_same_thread=False)
        self.annotated_conn.row_factory = sqlite3.Row
        self.source_conn = sqlite3.connect(cfg.source_db, check_same_thread=False)
        self.source_conn.row_factory = sqlite3.Row

        self.annotated_columns = self._load_columns(
            self.annotated_conn, cfg.annotated_table
        )
        self.source_columns = self._load_columns(self.source_conn, cfg.source_table)
        self.meta_cache: Dict[int, Dict[str, object]] = {}
        self.palette = TAG_COLORS.copy()

    @staticmethod
    def _load_columns(conn: sqlite3.Connection, table: str) -> Set[str]:
        rows = conn.execute(f"PRAGMA table_info({table});").fetchall()
        return {r["name"] for r in rows}

    def close(self) -> None:
        self.annotated_conn.close()
        self.source_conn.close()

    def _searchable_columns(self, filter_key: Optional[str]) -> List[str]:
        base_cols = (
            ["extracted_text_full"]
            if "extracted_text_full" in self.annotated_columns
            else []
        )

        if filter_key and filter_key in self.annotated_columns:
            base_cols = [filter_key]

        deps = DEPENDENT_FILTERS.get(filter_key or "", [])
        cols = base_cols + [c for c in deps if c in self.annotated_columns]
        # Guarantee fallback
        if not cols:
            cols = (
                ["extracted_text_full"]
                if "extracted_text_full" in self.annotated_columns
                else []
            )
        return cols

    def _nonempty_filter_clause(self, filter_key: Optional[str]) -> str:
        if (
            filter_key
            and filter_key in ABSOLUTE_FILTERS
            and filter_key in self.annotated_columns
        ):
            return f"COALESCE(NULLIF(TRIM({filter_key}), ''), '') <> ''"
        return ""

    def _resolve_allowed_tags(self, filter_key: Optional[str]) -> Optional[Set[str]]:
        if not filter_key:
            return None
        primary = FILTER_ALIASES.get(filter_key.lower())
        if primary is None or primary not in self.annotated_columns:
            raise ValueError(f"Unknown or unavailable filter: {filter_key}")
        tags = {primary}
        tags.update(DEPENDENT_FILTERS.get(primary, []))
        return tags

    def _build_like_clause(
        self, columns: Sequence[str], search_term: str
    ) -> Tuple[str, List[str]]:
        like_term = f"%{search_term}%"
        conditions = [f"LOWER(COALESCE({col}, '')) LIKE ?" for col in columns]
        return " OR ".join(conditions), [like_term] * len(columns)

    def _count(self, where_clause: str, params: Sequence[str]) -> int:
        row = self.annotated_conn.execute(
            f"SELECT COUNT(*) AS c FROM {self.cfg.annotated_table} WHERE {where_clause}",
            params,
        ).fetchone()
        return int(row["c"]) if row else 0

    def _fetch_rows(
        self,
        where_clause: str,
        params: Sequence[str],
        limit: int,
        offset: int,
    ) -> List[sqlite3.Row]:
        return self.annotated_conn.execute(
            f"""
            SELECT id, extracted_text_full
            FROM {self.cfg.annotated_table}
            WHERE {where_clause}
            ORDER BY id
            LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        ).fetchall()

    def _get_metadata(self, global_id: int) -> Dict[str, object]:
        if global_id in self.meta_cache:
            return self.meta_cache[global_id]

        meta = {
            "sura_number": None,
            "sura_name": None,
            "ayah_number": None,
            "ayah_text": None,
        }
        if {"sura", "aya"}.issubset(self.source_columns):
            row = self.source_conn.execute(
                f"SELECT sura, aya, text FROM {self.cfg.source_table} WHERE id = ?",
                (global_id,),
            ).fetchone()
            if row:
                sura_num = row["sura"]
                ayah_num = row["aya"]
                meta.update(
                    {
                        "sura_number": sura_num,
                        "sura_name": (
                            SURAH_NAMES[sura_num - 1]
                            if 1 <= sura_num <= len(SURAH_NAMES)
                            else None
                        ),
                        "ayah_number": ayah_num,
                        "ayah_text": strip_html(row["text"]),
                    }
                )

        self.meta_cache[global_id] = meta
        return meta

    def _fetch_xml_for_mode(
        self, global_id: int, base_row: sqlite3.Row, mode: str
    ) -> str:
        if mode == "full":
            return base_row["extracted_text_full"] or ""
        if mode == "section":
            return base_row["extracted_text_full"] or ""
        if mode == "blocks":
            rows = self.annotated_conn.execute(
                f"SELECT block FROM {self.cfg.blocks_table} WHERE tafsir_section_id = ? ORDER BY rowid",
                (global_id,),
            ).fetchall()
            blocks = [r["block"] for r in rows if r["block"]]
            if not blocks:
                return ""
            inner = "\n\n".join(blocks)
            return f"<tafsir_section>{inner}</tafsir_section>"
        if mode == "chunks":
            rows = self.annotated_conn.execute(
                f"""
                SELECT b.id AS block_id, c.chunk
                FROM {self.cfg.chunks_table} AS c
                JOIN {self.cfg.blocks_table} AS b
                  ON c.tafsir_block_id = b.id
                WHERE b.tafsir_section_id = ?
                ORDER BY b.rowid, c.rowid
                """,
                (global_id,),
            ).fetchall()
            if not rows:
                return ""
            blocks: Dict[int, List[str]] = {}
            for r in rows:
                bid = int(r["block_id"])
                blocks.setdefault(bid, []).append(r["chunk"] or "")
            parts: List[str] = []
            for _, chunk_list in blocks.items():
                block_content = "".join(chunk_list)
                if block_content.strip():
                    parts.append(f"<tafsir_section_block>{block_content}</tafsir_section_block>")
            if not parts:
                return ""
            return f"<tafsir_section>{''.join(parts)}</tafsir_section>"
        raise ValueError(f"Unsupported mode '{mode}'")

    @staticmethod
    def _structural_markers(mode: str, filter_key: Optional[str]) -> Set[str]:
        if filter_key:
            return set()
        if mode == "section":
            return {"tafsir_section"}
        if mode == "blocks":
            return {"tafsir_section", "tafsir_section_block"}
        if mode == "chunks":
            return {"tafsir_section", "tafsir_section_block", "tafsir_chunk"}
        return set()

    def _record_from_row(
        self,
        row: sqlite3.Row,
        allowed_tags: Optional[Set[str]],
        mode: str,
        highlight: bool,
        filter_key: Optional[str],
    ) -> Dict[str, object]:
        global_id = int(row["id"])
        xml_source = self._fetch_xml_for_mode(global_id, row, mode)

        plain_text, plain_tags = render_xml_text(
            xml_source, allowed_tags=allowed_tags, highlight=False, palette=self.palette
        )
        if highlight:
            structural_markers = self._structural_markers(mode, filter_key)
            rendered_html, used_tags = render_xml_text(
                xml_source,
                allowed_tags=allowed_tags,
                highlight=True,
                palette=self.palette,
                structural_markers=structural_markers,
            )
        else:
            rendered_html, used_tags = plain_text, plain_tags

        tags_used = sorted(set(plain_tags) | set(used_tags))
        meta = self._get_metadata(global_id)

        return {
            "id": global_id,
            "mode": mode,
            "filter": list(allowed_tags) if allowed_tags else [],
            "tafsir": self.cfg.key,
            "content_plain": plain_text,
            "content_html": rendered_html,
            "tags": tags_used,
            **meta,
        }

    def _palette_for(self, tags: Sequence[str]) -> Dict[str, str]:
        return {tag: color_for_tag(tag) for tag in tags}

    def search(
        self,
        query: str,
        limit: int,
        offset: int,
        filter_key: Optional[str],
        mode: str,
        highlight: bool,
    ) -> Dict[str, object]:
        raw_query = (query or "").strip()
        norm_query = normalize(raw_query)
        if len(norm_query) < 2:
            raise ValueError("query too short; provide at least 2 characters")

        allowed_tags = self._resolve_allowed_tags(filter_key) if filter_key else None
        search_cols = self._searchable_columns(filter_key)
        clause, params = self._build_like_clause(search_cols, raw_query.lower())
        total = self._count(clause, params)
        rows = self._fetch_rows(clause, params, limit=limit, offset=offset)
        results: List[Dict[str, object]] = []
        for row in rows:
            rec = self._record_from_row(
                row,
                allowed_tags=allowed_tags,
                mode=mode,
                highlight=highlight,
                filter_key=filter_key,
            )
            if (
                filter_key in ABSOLUTE_FILTERS
                and not str(rec.get("content_plain", "")).strip()
            ):
                continue
            results.append(rec)
        used_palette = self._palette_for(
            sorted({tag for r in results for tag in r.get("tags", [])})
        )
        return {
            "query": query,
            "normalized_query": norm_query,
            "filter": filter_key,
            "mode": mode,
            "highlight": highlight,
            "offset": offset,
            "limit": limit,
            "returned": len(results),
            "total": total,
            "palette": used_palette,
            "results": results,
        }

    def browse(
        self,
        limit: int,
        offset: int,
        filter_key: Optional[str],
        mode: str,
        highlight: bool,
    ) -> Dict[str, object]:
        allowed_tags = self._resolve_allowed_tags(filter_key) if filter_key else None
        clause = self._nonempty_filter_clause(filter_key)
        where_stmt = f"WHERE {clause}" if clause else ""
        total_row = self.annotated_conn.execute(
            f"SELECT COUNT(*) AS c FROM {self.cfg.annotated_table} {where_stmt}"
        ).fetchone()
        total = int(total_row["c"]) if total_row else 0
        rows = self.annotated_conn.execute(
            f"""
            SELECT id, extracted_text_full
            FROM {self.cfg.annotated_table}
            {where_stmt}
            ORDER BY id
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        results: List[Dict[str, object]] = []
        for row in rows:
            rec = self._record_from_row(
                row,
                allowed_tags=allowed_tags,
                mode=mode,
                highlight=highlight,
                filter_key=filter_key,
            )
            if (
                filter_key in ABSOLUTE_FILTERS
                and not str(rec.get("content_plain", "")).strip()
            ):
                continue
            results.append(rec)
        used_palette = self._palette_for(
            sorted({tag for r in results for tag in r.get("tags", [])})
        )
        return {
            "query": None,
            "filter": filter_key,
            "mode": mode,
            "highlight": highlight,
            "offset": offset,
            "limit": limit,
            "returned": len(results),
            "total": total,
            "palette": used_palette,
            "results": results,
        }

    def get_one(
        self,
        global_id: int,
        filter_key: Optional[str],
        mode: str,
        highlight: bool,
    ) -> Dict[str, object]:
        row = self.annotated_conn.execute(
            f"SELECT id, extracted_text_full FROM {self.cfg.annotated_table} WHERE id = ?",
            (global_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="record not found")
        allowed_tags = self._resolve_allowed_tags(filter_key) if filter_key else None
        record = self._record_from_row(
            row,
            allowed_tags=allowed_tags,
            mode=mode,
            highlight=highlight,
            filter_key=filter_key,
        )
        if (
            filter_key in ABSOLUTE_FILTERS
            and not str(record.get("content_plain", "")).strip()
        ):
            raise HTTPException(status_code=404, detail="record not found")
        record["palette"] = self._palette_for(record.get("tags", []))
        return record


class TafsirManager:
    def __init__(self, configs: Dict[str, TafsirConfig], default_key: str):
        if not configs:
            raise RuntimeError("No tafsir configurations available")
        self.configs = configs
        self.default = default_key if default_key in configs else next(iter(configs))
        self._repos: Dict[str, TafsirRepository] = {}

    def list_keys(self) -> List[str]:
        return sorted(self.configs.keys())

    def _select_keys(self, key: Optional[str]) -> List[str]:
        if not key:
            return [self.default]
        key = key.lower()
        if key == "all":
            return self.list_keys()
        if key not in self.configs:
            raise HTTPException(status_code=400, detail=f"Unknown tafsir '{key}'")
        return [key]

    def _repo(self, key: str) -> TafsirRepository:
        if key not in self._repos:
            self._repos[key] = TafsirRepository(self.configs[key])
        return self._repos[key]

    def close(self) -> None:
        for repo in self._repos.values():
            repo.close()

    def _aggregate(
        self,
        method: str,
        keys: List[str],
        *,
        limit: int,
        offset: int,
        **kwargs,
    ) -> Dict[str, object]:
        per_repo_limit = limit + offset
        combined_results: List[Dict[str, object]] = []
        palette: Dict[str, str] = {}
        total = 0

        for key in keys:
            repo = self._repo(key)
            fn = getattr(repo, method)
            data = fn(limit=per_repo_limit, offset=0, **kwargs)
            total += data.get("total", 0)
            palette.update(data.get("palette") or {})
            combined_results.extend(data.get("results") or [])

        combined_results.sort(key=lambda r: (r.get("id", 0), r.get("tafsir", "")))
        sliced = combined_results[offset : offset + limit]

        return {
            "query": kwargs.get("query"),
            "filter": kwargs.get("filter_key"),
            "mode": kwargs.get("mode"),
            "highlight": kwargs.get("highlight"),
            "offset": offset,
            "limit": limit,
            "returned": len(sliced),
            "total": total,
            "palette": palette,
            "results": sliced,
            "tafsir": keys if len(keys) > 1 else keys[0],
        }

    def columns_for(self, keys: List[str]) -> Set[str]:
        cols: Set[str] = set()
        for key in keys:
            cols.update(self._repo(key).annotated_columns)
        return cols

    def search(
        self,
        *,
        tafsir: Optional[str],
        query: str,
        limit: int,
        offset: int,
        filter_key: Optional[str],
        mode: str,
        highlight: bool,
    ) -> Dict[str, object]:
        keys = self._select_keys(tafsir)
        if len(keys) == 1:
            data = self._repo(keys[0]).search(
                query=query,
                limit=limit,
                offset=offset,
                filter_key=filter_key,
                mode=mode,
                highlight=highlight,
            )
            data["tafsir"] = keys[0]
            data["available_tafsirs"] = self.list_keys()
            return data
        data = self._aggregate(
            "search",
            keys,
            limit=limit,
            offset=offset,
            query=query,
            filter_key=filter_key,
            mode=mode,
            highlight=highlight,
        )
        data["available_tafsirs"] = self.list_keys()
        return data

    def browse(
        self,
        *,
        tafsir: Optional[str],
        limit: int,
        offset: int,
        filter_key: Optional[str],
        mode: str,
        highlight: bool,
    ) -> Dict[str, object]:
        keys = self._select_keys(tafsir)
        if len(keys) == 1:
            data = self._repo(keys[0]).browse(
                limit=limit,
                offset=offset,
                filter_key=filter_key,
                mode=mode,
                highlight=highlight,
            )
            data["tafsir"] = keys[0]
            data["available_tafsirs"] = self.list_keys()
            return data
        data = self._aggregate(
            "browse",
            keys,
            limit=limit,
            offset=offset,
            filter_key=filter_key,
            mode=mode,
            highlight=highlight,
        )
        data["available_tafsirs"] = self.list_keys()
        return data

    def get_one(
        self,
        *,
        tafsir: Optional[str],
        global_id: int,
        filter_key: Optional[str],
        mode: str,
        highlight: bool,
    ) -> Dict[str, object]:
        keys = self._select_keys(tafsir)
        last_exc: Optional[Exception] = None
        for key in keys:
            try:
                data = self._repo(key).get_one(
                    global_id=global_id,
                    filter_key=filter_key,
                    mode=mode,
                    highlight=highlight,
                )
                data["tafsir"] = key
                data["available_tafsirs"] = self.list_keys()
                return data
            except HTTPException as exc:
                last_exc = exc
                continue
        if isinstance(last_exc, HTTPException):
            raise last_exc
        raise HTTPException(status_code=404, detail="record not found")


# ---------------- FastAPI setup ----------------

app = FastAPI(title="Tafsir XML Search API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TAFSIR_CONFIGS = discover_tafsir_configs()
tafsir_manager = TafsirManager(TAFSIR_CONFIGS, default_key=DEFAULT_TAFSIR.lower())

app.mount("/static", StaticFiles(directory="static"), name="static")

logger = logging.getLogger("tafsir")
logging.basicConfig(level=logging.INFO)


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):  # type: ignore[override]
    logger.error("Unhandled error: %s", exc, exc_info=True)
    return JSONResponse({"detail": "Internal server error"}, status_code=500)


@app.get("/")
async def root():
    return FileResponse("static/viewer.html")


@app.get("/health")
async def health():
    default_repo = tafsir_manager._repo(tafsir_manager.default)
    return {
        "status": "ok",
        "default_tafsir": tafsir_manager.default,
        "available_tafsirs": tafsir_manager.list_keys(),
        "annotated_db": default_repo.cfg.annotated_db,
        "source_db": default_repo.cfg.source_db,
        "annotated_table": default_repo.cfg.annotated_table,
        "source_table": default_repo.cfg.source_table,
        "available_columns": sorted(default_repo.annotated_columns),
    }


def _validate_mode(mode: str) -> str:
    mode = (mode or "full").lower()
    if mode not in {"full", "section", "blocks", "chunks"}:
        raise HTTPException(
            status_code=400, detail="mode must be one of: full, section, blocks, chunks"
        )
    return mode


def _validate_filter(
    filter_key: Optional[str], selection_keys: List[str]
) -> Optional[str]:
    if not filter_key:
        return None
    key = filter_key.lower()
    mapped = FILTER_ALIASES.get(key)
    if mapped is None:
        raise HTTPException(status_code=400, detail="Invalid filter")
    available_cols = tafsir_manager.columns_for(selection_keys)
    if mapped not in available_cols:
        raise HTTPException(
            status_code=400, detail="Filter not available for selected tafsir"
        )
    return mapped


@app.get("/api/search")
async def api_search(
    q: str = Query(..., description="Search query (min 2 letters)"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    mode: str = Query("full"),
    filter: Optional[str] = Query(None, alias="filter"),
    highlight: bool = Query(True),
    tafsir: Optional[str] = Query(None),
):
    mode = _validate_mode(mode)
    selection_keys = tafsir_manager._select_keys(tafsir)
    filter_key = _validate_filter(filter, selection_keys)
    try:
        return tafsir_manager.search(
            tafsir=tafsir,
            query=q,
            limit=limit,
            offset=offset,
            filter_key=filter_key,
            mode=mode,
            highlight=highlight,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/browse")
async def api_browse(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    mode: str = Query("full"),
    filter: Optional[str] = Query(None, alias="filter"),
    highlight: bool = Query(True),
    tafsir: Optional[str] = Query(None),
):
    mode = _validate_mode(mode)
    selection_keys = tafsir_manager._select_keys(tafsir)
    filter_key = _validate_filter(filter, selection_keys)
    return tafsir_manager.browse(
        tafsir=tafsir,
        limit=limit,
        offset=offset,
        filter_key=filter_key,
        mode=mode,
        highlight=highlight,
    )


@app.get("/api/verse/{global_id}")
async def api_get_one(
    global_id: int,
    mode: str = Query("full"),
    filter: Optional[str] = Query(None, alias="filter"),
    highlight: bool = Query(True),
    tafsir: Optional[str] = Query(None),
):
    mode = _validate_mode(mode)
    selection_keys = tafsir_manager._select_keys(tafsir)
    filter_key = _validate_filter(filter, selection_keys)
    return tafsir_manager.get_one(
        tafsir=tafsir,
        global_id=global_id,
        filter_key=filter_key,
        mode=mode,
        highlight=highlight,
    )


@app.on_event("shutdown")
def _shutdown():
    tafsir_manager.close()


# Gunicorn/Uvicorn entrypoint helper:
def get_app():
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
