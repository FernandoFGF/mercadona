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
