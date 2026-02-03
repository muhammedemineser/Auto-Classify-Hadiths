from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Iterable, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]  # repository root
PROJECT_ROOT = REPO_ROOT / "Tafsir"

# Modules that are optional or heavy in tests; we stub them so import resolution
# checks focus on our own package structure rather than external hardware/API deps.
STUB_MODULES = [
    "pyautogui",
    "pyperclip",
    "mss",
    "google",
    "google.genai",
    "google.genai.types",
    "fastapi",
    "fastapi.middleware",
    "fastapi.middleware.cors",
    "fastapi.responses",
    "fastapi.staticfiles",
    "uvicorn",
    "sqlalchemy",
    "bs4",
    "regex",
]


def _ensure_stub(mod_name: str) -> None:
    parts = mod_name.split(".")
    for i in range(1, len(parts) + 1):
        sub = ".".join(parts[:i])
        if sub not in sys.modules:
            sys.modules[sub] = ModuleType(sub)


for _mod in STUB_MODULES:
    _ensure_stub(_mod)

# Make sure project root is importable
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _module_name_for(path: Path) -> str:
    rel = path.relative_to(REPO_ROOT).with_suffix("")
    return ".".join(rel.parts)


def _resolve_relative_module(path: Path, node: ast.ImportFrom) -> str | None:
    base = _module_name_for(path)
    pkg_parts = base.split(".")[:-1]  # package components
    if node.level > len(pkg_parts):
        return None
    pkg_parts = pkg_parts[: len(pkg_parts) - node.level + 1]
    if node.module:
        pkg_parts.append(node.module)
    return ".".join(pkg_parts)


def _spec_exists(module_name: str) -> bool:
    if not module_name:
        return True
    if module_name in sys.modules:
        return True
    return importlib.util.find_spec(module_name) is not None


def check_imports(py_path: Path) -> List[str]:
    problems: List[str] = []
    tree = ast.parse(py_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not _spec_exists(alias.name):
                    problems.append(f"ImportError: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            target = node.module or ""
            if node.level:
                target = _resolve_relative_module(py_path, node)
            if target and not _spec_exists(target):
                problems.append(f"ImportError: {target}")
    return problems


PATH_KEYS = [".sqlite3", ".json", ".yaml", ".yml", ".toml", ".ini", ".env", "logs/"]


def looks_like_path(val: str) -> bool:
    return any(key in val for key in PATH_KEYS)


def check_paths(py_path: Path) -> List[str]:
    problems: List[str] = []
    tree = ast.parse(py_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            val = node.value
            if "\n" in val:
                continue  # skip multi-line docstrings
            if not looks_like_path(val):
                continue
            if not val or val.startswith("*"):
                continue
            candidate = Path(val)
            if not candidate.is_absolute():
                # Skip bare filenames; many are created dynamically in tests.
                if "/" not in val and "\\" not in val:
                    continue
                for base in (REPO_ROOT, PROJECT_ROOT):
                    test_path = (base / val).resolve()
                    if test_path.exists():
                        candidate = test_path
                        break
                else:
                    candidate = (REPO_ROOT / val).resolve()
            if not candidate.exists():
                problems.append(f"Missing path: {candidate}")
    return problems


def iter_python_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*.py"):
        parts = set(path.parts)
        if any(skip in parts for skip in {".venv", "__pycache__", ".git", ".pytest_cache"}):
            continue
        yield path


def main() -> int:
    failures: List[Tuple[Path, List[str]]] = []
    for py_path in iter_python_files(REPO_ROOT):
        import_errors = check_imports(py_path)
        path_errors = check_paths(py_path)
        errors = import_errors + path_errors
        if errors:
            failures.append((py_path, errors))

    if failures:
        for py_path, errs in failures:
            rel = py_path.relative_to(REPO_ROOT)
            print(f"[FAILED] {rel}")
            for err in errs:
                print(f"  - {err}")
        return 1

    print("All imports and referenced paths resolved successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
