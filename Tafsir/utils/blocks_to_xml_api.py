"""API-facing wrapper for Gemini tafsir conversion helpers.

This module aliases ``blocks_to_xml_gui`` so legacy imports continue to work and
monkeypatching affects the real implementation.
"""

import importlib
import sys

# Load environment variables early (e.g., GEMINI keys, DB paths)
try:  # optional dependency
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

_impl = importlib.import_module("Tafsir.pipeline.gemini_gui.blocks_to_xml_gui")
sys.modules[__name__] = _impl
