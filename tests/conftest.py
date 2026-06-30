"""
Fixtures compartidos: paths temporales para que los tests no toquen la
cache real del usuario.
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    """Redirige config.DATA_DIR a un directorio temporal."""
    import config
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "PRODUCTS_CACHE", tmp_path / "products_cache.json")
    monkeypatch.setattr(config, "CACHE_DB", tmp_path / "cache.db")
    (tmp_path).mkdir(exist_ok=True)
    return tmp_path
