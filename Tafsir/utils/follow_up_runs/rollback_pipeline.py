"""Shim to preserve the old import path ``Tafsir.utils.follow_up_runs.rollback_pipeline``.

The implementation now lives under
``Tafsir.pipeline.analysis.data_cleaning.rollback_pipeline``.
This module forwards the import to the implementation so attribute
assignments (e.g. monkeypatch in tests) affect the real module.
"""

import importlib
import sys

_impl = importlib.import_module(
    "Tafsir.pipeline.analysis.data_cleaning.rollback_pipeline"
)
sys.modules[__name__] = _impl
