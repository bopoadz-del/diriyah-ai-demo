import sys


def test_backend_main_imports_cleanly():
    sys.modules.pop("matplotlib", None)
    sys.modules.pop("matplotlib.pyplot", None)
    import backend.main  # noqa: F401
    assert "matplotlib" not in sys.modules
    assert "matplotlib.pyplot" not in sys.modules


def test_backend_backend_main_imports_cleanly():
    import backend.backend.main  # noqa: F401
