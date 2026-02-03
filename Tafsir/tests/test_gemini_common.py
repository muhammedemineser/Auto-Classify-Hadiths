import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Tafsir.pipeline.gemini_common import clean_wrapped_xml


def test_clean_wrapped_xml_strips_fences_and_xml_keyword():
    raw = "  ```xml<tafsir_section_block>foo</tafsir_section_block> ```"
    assert clean_wrapped_xml(raw) == "<tafsir_section_block>foo</tafsir_section_block>"


def test_clean_wrapped_xml_handles_none():
    assert clean_wrapped_xml(None) is None


def test_clean_wrapped_xml_removes_xml_declaration():
    raw = '<?xml version="1.0" encoding="UTF-8"?><tafsir_section_block>foo</tafsir_section_block>'
    assert clean_wrapped_xml(raw) == "<tafsir_section_block>foo</tafsir_section_block>"
