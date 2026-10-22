import importlib

import pytest


@pytest.mark.parametrize("module", [
    "app.config", "app.database.connection", "app.database.models",
    "app.data_sources", "app.services", "app.ml", "app.dashboard", "scripts.init_db",
])
def test_imports(module):
    assert importlib.import_module(module) is not None

