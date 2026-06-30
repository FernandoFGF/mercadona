"""Tests del product matcher: mockeando mercadona_cli."""
from unittest.mock import patch

import pytest

from core import product_matcher


HITS = [
    {"id": 1, "display_name": "Arroz redondo Hacendado", "unit_price": 1.20},
    {"id": 2, "display_name": "Arroz largo Hacendado", "unit_price": 1.35},
    {"id": 3, "display_name": "Pasta espagueti Hacendado", "unit_price": 0.95},
]


@pytest.fixture(autouse=True)
def disable_semantic():
    """Desactiva el matching semántico para no hacer llamadas HTTP reales."""
    with patch("core.product_matcher.semantic_matcher.match_semantic", return_value=None):
        yield


@pytest.fixture
def mocked_search():
    with patch("core.product_matcher.mercadona_cli.search") as m:
        m.return_value = HITS
        yield m


def test_match_returns_best_hit(mocked_search):
    res = product_matcher.match("arroz redondo")
    assert res is not None
    assert res["id"] == 1
    assert "arroz" in res["name"].lower()


def test_match_returns_normalized_shape(mocked_search):
    res = product_matcher.match("arroz")
    expected = {"id", "name", "price", "unit_price", "raw", "match_kind"}
    assert set(res.keys()) == expected
    assert res["match_kind"] in ("semantic", "fuzzy", "fallback")


def test_match_no_hits_returns_none():
    with patch("core.product_matcher.mercadona_cli.search", return_value=[]):
        assert product_matcher.match("xyz123") is None


def test_match_low_score_falls_back_to_first_hit():
    weak = [{"id": 9, "display_name": "Algo totalmente distinto", "unit_price": 5.0}]
    with patch("core.product_matcher.mercadona_cli.search", return_value=weak):
        res = product_matcher.match("leche")
        assert res is not None
        assert res["id"] == 9


def test_match_many_returns_one_per_ingredient(mocked_search):
    res = product_matcher.match_many(["arroz redondo", "pasta"])
    assert len(res) == 2
    assert res[0]["id"] in (1, 2)
    assert res[1]["id"] == 3


def test_match_many_uses_fresh_flag(mocked_search):
    product_matcher.match_many(["arroz"], fresh=True)
    mocked_search.assert_called_with("arroz", limit=5, fresh=True)
