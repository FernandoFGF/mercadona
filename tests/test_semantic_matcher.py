"""Tests del semantic matcher (sin llamadas HTTP reales)."""
from unittest.mock import patch
import numpy as np

import pytest

from core import semantic_matcher


HITS = [
    {"id": 1, "display_name": "Tomate triturado Hacendado"},
    {"id": 2, "display_name": "Tomate frito Solis"},
    {"id": 3, "display_name": "Pasta espagueti"},
]


@pytest.fixture(autouse=True)
def enable_semantic(monkeypatch):
    monkeypatch.setattr(semantic_matcher, "_is_enabled", lambda: True)
    # Reset state
    semantic_matcher._negative_cache.clear()
    semantic_matcher._recent_429.clear()
    semantic_matcher._circuit_open_until = 0.0


def test_match_semantic_returns_best(monkeypatch):
    """Embedding idéntico al del producto debe ganar."""
    base_vec = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    other_vec = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    def fake_embed(text):
        if "tomate" in text.lower() and "pasta" not in text.lower():
            return base_vec
        return other_vec

    with patch.object(semantic_matcher, "_get_or_compute_embedding", side_effect=fake_embed):
        best = semantic_matcher.match_semantic("tomate triturado", HITS, min_score=0.5)
    assert best is not None
    assert best["id"] in (1, 2)


def test_match_semantic_below_threshold(monkeypatch):
    """Si todos los scores están por debajo del umbral, devuelve None."""
    a = np.array([1.0, 0.0], dtype=np.float32)
    b = np.array([0.0, 1.0], dtype=np.float32)  # ortogonal a la query

    def fake_embed(text):
        return a if text == "tomate" else b

    with patch.object(semantic_matcher, "_get_or_compute_embedding", side_effect=fake_embed):
        best = semantic_matcher.match_semantic("tomate", HITS, min_score=0.5)
    assert best is None


def test_match_semantic_no_hits():
    assert semantic_matcher.match_semantic("x", []) is None


def test_match_semantic_disabled(monkeypatch):
    monkeypatch.setattr(semantic_matcher, "_is_enabled", lambda: False)
    assert semantic_matcher.match_semantic("x", HITS) is None


def test_cosine_identical_is_one():
    v = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    assert semantic_matcher._cosine(v, v) == pytest.approx(1.0)


def test_cosine_orthogonal_is_zero():
    a = np.array([1.0, 0.0], dtype=np.float32)
    b = np.array([0.0, 1.0], dtype=np.float32)
    assert semantic_matcher._cosine(a, b) == pytest.approx(0.0)


def test_cosine_zero_vector():
    a = np.array([0.0, 0.0], dtype=np.float32)
    b = np.array([1.0, 2.0], dtype=np.float32)
    assert semantic_matcher._cosine(a, b) == 0.0


def test_429_registers_in_negative_cache():
    semantic_matcher._register_429("patata")
    assert semantic_matcher._is_cached_429("patata") is True
    assert semantic_matcher._is_cached_429("cebolla") is False


def test_circuit_breaker_opens_after_3_429s():
    for term in ("a", "b", "c"):
        semantic_matcher._register_429(term)
    assert semantic_matcher.circuit_is_open() is True


def test_circuit_breaker_does_not_open_below_threshold():
    semantic_matcher._register_429("a")
    semantic_matcher._register_429("b")
    assert semantic_matcher.circuit_is_open() is False


def test_reset_circuit_clears_breaker():
    for term in ("a", "b", "c"):
        semantic_matcher._register_429(term)
    assert semantic_matcher.circuit_is_open() is True
    semantic_matcher.reset_circuit()
    assert semantic_matcher.circuit_is_open() is False


def test_disabled_via_settings(monkeypatch):
    """Si el setting usar_embeddings=False, _is_enabled devuelve False."""
    # Sobrescribimos settings_get directamente en el módulo
    def fake_get(key):
        return False if key == "usar_embeddings" else True
    monkeypatch.setattr("core.semantic_matcher.settings_get", fake_get)
    # Forzamos _is_enabled a NO usar el mock de enable_semantic
    monkeypatch.setattr(semantic_matcher, "_is_enabled",
                        semantic_matcher._is_enabled.__wrapped__ if hasattr(semantic_matcher._is_enabled, "__wrapped__") else semantic_matcher._is_enabled)
    # Llamada real: con key vacia y circuit cerrado, debe devolver False
    semantic_matcher._circuit_open_until = 0.0
    # El test solo valida la lógica de settings: si el setting es False, no debe habilitar
    # Reimportamos el módulo real para testear
    from importlib import reload
    import core.semantic_matcher as sm
    reload(sm)
    monkeypatch.setattr(sm, "settings_get", fake_get)
    assert sm._is_enabled() is False
