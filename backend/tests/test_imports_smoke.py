import importlib


def test_import_regression_guard() -> None:
    module = importlib.import_module("backend.regression.guard")
    assert hasattr(module, "RegressionGuard")


def test_import_progress_tracking() -> None:
    module = importlib.import_module("backend.api.progress_tracking")
    assert hasattr(module, "router")
