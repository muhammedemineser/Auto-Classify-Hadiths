from pathlib import Path

from tools.tafsir_gui.core.artifacts import ArtifactStore


def test_artifacts_versioning(tmp_path: Path):
    store = ArtifactStore(tmp_path)
    p1 = store.save_json("schema", {"a": 1})
    p2 = store.save_json("schema", {"a": 2})
    assert p1 != p2
    assert p2.exists()
    assert store.latest("schema") == p2


def test_prompt_mode_saves_new_version(tmp_path: Path):
    store = ArtifactStore(tmp_path)
    seed = store.save_text("prompt_legacy", "legacy")
    new = store.save_text("prompt_universal", "universal")
    assert seed != new
    assert store.latest("prompt_universal") == new
