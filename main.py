import sys
import subprocess
from Tafsir.pipeline import app

COMMANDS = {
    "NiceUI": [sys.executable, "-m", "tools.tafsir_gui.main"],
    "test_NiceUI": [sys.executable, "-m", "pytest", "tools"],
    "gui": [sys.executable, "-m", "Tafsir.pipeline.gemini_gui.blocks_to_xml_gui"],
    "api": [sys.executable, "-m", "Tafsir.pipeline.gemini_api.blocks_to_xml_api"],
    "rollback": [
        sys.executable,
        "-m",
        "Tafsir.pipeline.analysis.data_cleaning.rollback_pipeline",
    ],
    "app": [sys.executable, "-m", "uvicorn", "Tafsir.pipeline.app:app", "--reload"],
}


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: python main.py [{'|'.join(COMMANDS.keys())}]")
    name = sys.argv[1]
    cmd = COMMANDS[name]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
