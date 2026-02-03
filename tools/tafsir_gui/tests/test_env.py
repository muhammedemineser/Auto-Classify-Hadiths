from pathlib import Path

from tools.tafsir_gui.utils import env


def test_write_and_read_env(tmp_path: Path):
    env_path = tmp_path / ".env"
    env.write_env({"FOO": "bar", "X": "1"}, path=env_path)
    env.write_env({"FOO": "baz"}, path=env_path)
    data = env.read_env(env_path)
    assert data["FOO"] == "baz"
    assert data["X"] == "1"


def test_mask_secret():
    assert env.mask_secret("abcdef") == "******"
