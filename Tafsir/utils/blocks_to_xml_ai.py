"""Compatibility wrapper for legacy imports.

Historically the project imported ``blocks_to_xml_ai`` from a ``utils`` folder.
The implementation now lives in ``Tafsir.pipeline.gemini_gui.blocks_to_xml_gui``.
We alias this module so attribute access *and assignments* (monkeypatching) hit
the real implementation.
"""

import importlib
import sys

_impl = importlib.import_module("Tafsir.pipeline.gemini_gui.blocks_to_xml_gui")
sys.modules[__name__] = _impl
