import re
from pathlib import Path

log_file = Path(
    "/home/muhammed-emin-eser/desk/apps/classify/Tafsir/utils/second_run/blocks_to_xml_continue.py"
)

pattern = re.compile(r'(?:_write_log|print)\(\s*([\'"])(.*?)\1\s*\)')

text = log_file.read_text(encoding="utf-8", errors="replace")
for m in pattern.finditer(text):
    print(m.group(2))
