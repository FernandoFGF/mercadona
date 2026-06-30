"""Tests del wrapper mercadona-cli: mockeando subprocess."""
import json
from unittest.mock import patch, MagicMock

import pytest

from adapters import mercadona_cli


def _proc(returncode=0, stdout="{}", stderr=""):
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


def test_search_uses_cache_when_not_fresh(tmp_data_dir):
    mercadona_cli._cache_set("arroz", [{"id": 1, "name": "cached"}])
    with patch("adapters.mercadona_cli._run") as run:
        hits = mercadona_cli.search("arroz", limit=5)
    run.assert_not_called()
    assert hits == [{"id": 1, "name": "cached"}]


def test_search_bypasses_cache_when_fresh(tmp_data_dir):
    mercadona_cli._cache_set("arroz", [{"id": 1, "name": "cached"}])
    with patch("adapters.mercadona_cli._run", return_value=[{"id": 2, "name": "fresh"}]):
        hits = mercadona_cli.search("arroz", limit=5, fresh=True)
    assert hits == [{"id": 2, "name": "fresh"}]


def test_search_writes_cache_on_miss(tmp_data_dir):
    with patch("adapters.mercadona_cli._run", return_value={"hits": [{"id": 5, "name": "x"}]}):
        mercadona_cli.search("patatas", limit=5)
    cached = mercadona_cli._cache_get("patatas")
    assert cached == [{"id": 5, "name": "x"}]


def test_search_caps_to_limit(tmp_data_dir):
    big = [{"id": i, "name": f"p{i}"} for i in range(20)]
    with patch("adapters.mercadona_cli._run", return_value=big):
        hits = mercadona_cli.search("x", limit=3)
    assert len(hits) == 3


def test_cache_persists_across_instances(tmp_data_dir):
    mercadona_cli._cache_set("leche", [{"id": 9, "name": "L"}])
    mercadona_cli._CACHE.clear()
    mercadona_cli._CACHE_LOADED = False
    assert mercadona_cli._cache_get("leche") == [{"id": 9, "name": "L"}]


def test_cache_ttl_expiry(tmp_data_dir):
    mercadona_cli._cache_set("pan", [{"id": 1}])
    mercadona_cli._CACHE["pan"] = (0.0, [{"id": 1}])  # ts muy viejo
    assert mercadona_cli._cache_get("pan") is None


def test_clear_cache_wipes_disk(tmp_data_dir):
    mercadona_cli._cache_set("yogur", [{"id": 1}])
    assert mercadona_cli.is_cache_populated()
    mercadona_cli.clear_cache()
    assert not mercadona_cli.is_cache_populated()


def test_is_available_uses_shutil_which():
    with patch("adapters.mercadona_cli.shutil.which", return_value="/usr/bin/mercadona"):
        assert mercadona_cli.is_available() is True
    with patch("adapters.mercadona_cli.shutil.which", return_value=None):
        with patch("pathlib.Path.exists", return_value=False):
            assert mercadona_cli.is_available() is False
