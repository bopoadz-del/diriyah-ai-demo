import importlib


def test_import_vision_module() -> None:
    module = importlib.import_module("backend.services.vision")
    assert hasattr(module, "handle_vision")
