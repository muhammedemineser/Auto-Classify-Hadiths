import sys
import types

from tools.tafsir_gui.integrations.gemini import GeminiClient


def _install_fake_google():
    class FakeResponse:
        text = "pong"
        candidates = [1]

    class FakeModels:
        def generate_content(self, **kwargs):
            return FakeResponse()

    class FakeCaches:
        def create(self, **kwargs):
            return types.SimpleNamespace(name="cache/test", model=kwargs.get("model"))

    class FakeClient:
        def __init__(self, api_key=None):
            self.models = FakeModels()
            self.caches = FakeCaches()

    google_mod = types.ModuleType("google")
    genai_mod = types.ModuleType("google.genai")
    types_mod = types.ModuleType("google.genai.types")

    genai_mod.Client = FakeClient
    google_mod.genai = genai_mod
    types_mod.GenerateContentConfig = (
        lambda cached_content=None: {"cached_content": cached_content}
    )
    types_mod.CreateCachedContentConfig = lambda **kwargs: kwargs
    types_mod.Content = lambda **kwargs: kwargs
    types_mod.Part = lambda **kwargs: kwargs

    sys.modules["google"] = google_mod
    sys.modules["google.genai"] = genai_mod
    sys.modules["google.genai.types"] = types_mod


def test_generate_and_cache(monkeypatch):
    _install_fake_google()
    client = GeminiClient(api_key="dummy", cache_name=None, model_id="models/gemini-2.5-pro")
    assert client.test_call() == "pong"
    name = client.ensure_cache("prompt-prefix")
    assert name.startswith("cache/")
