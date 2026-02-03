import re
from pathlib import Path

from Tafsir.config import paths as cfg

log_file = cfg.PROJECT_ROOT / "pipeline" / "gemini_gui" / "blocks_to_xml_gui.py"

pattern = re.compile(r'(?:_write_log|print)\(\s*([\'"])(.*?)\1\s*\)')

text = log_file.read_text(encoding="utf-8", errors="replace")
for m in pattern.finditer(text):
    print(m.group(2))
