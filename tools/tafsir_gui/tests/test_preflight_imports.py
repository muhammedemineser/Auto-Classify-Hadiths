import importlib
import pkgutil
from pathlib import Path
from typing import List

import pytest


ENTRYPOINT_MODULES = [
    "tools.tafsir_gui.main",
    "tools.tafsir_gui.integrations.universal_pipeline",
    "Tafsir.pipeline.gemini_api.blocks_to_xml_api",
    "Tafsir.pipeline.gemini_gui.blocks_to_xml_gui",
    "Tafsir.pipeline.analysis.data_cleaning.rollback_pipeline",
]


def _collect_submodules(module_name: str) -> List[str]:
    """
    Ensure that all submodules reachable via pkgutil are imported so their dependencies
    are validated without hard-coding package names.
    """
    try:
        module = importlib.import_module(module_name)
    except Exception:  # let the test fail later with the same exception
        raise

    if not hasattr(module, "__path__"):
        return [module_name]

    names = [module_name]
    for finder, name, ispkg in pkgutil.walk_packages(
        module.__path__, prefix=module.__name__ + "."
    ):
        names.append(name)
    return names


@pytest.mark.parametrize("module_name", ENTRYPOINT_MODULES)
def test_entrypoint_imports(module_name: str):
    """
    Import each entry module and all reachable submodules so that missing dependencies
    anywhere in the import graph fail this test.
    """
    submodules = _collect_submodules(module_name)
    for name in submodules:
        importlib.import_module(name)
