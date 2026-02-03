"""
Helper to run the currently selected file as a module (equivalent to
`python -m package.module`) while keeping VS Code debugging conveniences.
Extra args after the file path are forwarded to the target module.

Usage (wired via launch.json):
    python run_active_as_module.py /abs/path/to/file.py
"""

from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path


def file_to_module(root: Path, file_path: Path) -> str:
    try:
        rel = file_path.relative_to(root)
    except ValueError:
        raise SystemExit(
            f"File {file_path} is outside project root {root}; cannot build module path."
        )

    parts = rel.with_suffix("").parts
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    if not parts:
        raise SystemExit("Could not derive module name from file path.")
    return ".".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a file as a module (like `python -m`) while forwarding extra args."
    )
    parser.add_argument("file", help="Absolute path to the Python file to run as a module")
    parser.add_argument(
        "--root",
        help="Project root (defaults to repo root adjacent to this script)",
    )
    args, passthrough = parser.parse_known_args()

    script_path = Path(__file__).resolve()
    default_root = script_path.parent  # repo root (we place this file there)
    root = Path(args.root).resolve() if args.root else default_root

    file_path = Path(args.file).resolve()
    if not file_path.is_file():
        raise SystemExit(f"File not found: {file_path}")

    module = file_to_module(root, file_path)

    # Ensure the root is on sys.path before running the module
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    # Forward any extra CLI args to the target module, mimicking `python -m`.
    sys.argv = [str(file_path), *passthrough]

    runpy.run_module(module, run_name="__main__", alter_sys=True)


if __name__ == "__main__":
    main()
