import sys


def test_no_heavy_imports_at_startup():
    import backend.main  # noqa: F401
    assert "torch" not in sys.modules
    assert "transformers" not in sys.modules
    assert "matplotlib" not in sys.modules
    assert "matplotlib.pyplot" not in sys.modules
