"""Tests de user_lists (pantry/avoid)."""
import pytest

from core.user_lists import PantryStore, AvoidStore


@pytest.fixture
def pantry(tmp_data_dir):
    return PantryStore()


@pytest.fixture
def avoid(tmp_data_dir):
    return AvoidStore()


def test_add_and_contains(pantry):
    assert pantry.add("arroz") is True
    assert pantry.contains("arroz") is True
    assert pantry.contains("ARROZ") is True
    assert pantry.contains("arroz basmati") is True  # fuzzy: token_set >= 85


def test_add_dedupes(pantry):
    assert pantry.add("arroz") is True
    assert pantry.add("arroz") is False
    assert pantry.add("Arroz") is False


def test_add_empty_rejected(pantry):
    assert pantry.add("") is False
    assert pantry.add("   ") is False


def test_remove(pantry):
    pantry.add("aceite")
    assert pantry.remove("aceite") is True
    assert pantry.contains("aceite") is False


def test_remove_missing(pantry):
    pantry.add("sal")
    assert pantry.remove("pimienta") is False


def test_filter_out(pantry):
    pantry.add("arroz")
    pantry.add("aceite")
    remaining = pantry.filter_out(["arroz", "leche", "aceite", "pan"])
    assert remaining == ["leche", "pan"]


def test_avoid_works(avoid):
    assert avoid.add("marisco") is True
    assert avoid.contains("mariscos") is True
    remaining = avoid.filter_out(["marisco", "arroz", "mariscos"])
    assert remaining == ["arroz"]


def test_persistence_across_instances(tmp_data_dir):
    p1 = PantryStore()
    p1.add("pasta")
    p2 = PantryStore()
    assert p2.contains("pasta") is True


def test_pantry_contains_matches_by_core(tmp_data_dir):
    """Si el usuario tiene 'vinagre', pantry.contains debe matchear con
    'vinagre de manzana', 'vinagre balsamico', etc. aunque el score
    fuzzy directo sea bajo."""
    p = PantryStore()
    p.add("vinagre")
    assert p.contains("vinagre de manzana") is True
    assert p.contains("vinagre balsamico de Modena") is True
    assert p.contains("vinagre de vino blanco") is True
    # Pero no debe matchear con algo sin relacion
    assert p.contains("aceite de oliva") is False


def test_pantry_filter_out_dedupes_variations(tmp_data_dir):
    """Variaciones de un mismo producto se filtran juntas si el core
    esta en pantry."""
    p = PantryStore()
    p.add("aceite")
    remaining = p.filter_out([
        "aceite de oliva virgen extra",
        "aceite de oliva",
        "vinagre de manzana",
        "tomate triturado",
    ])
    assert remaining == ["vinagre de manzana", "tomate triturado"]
