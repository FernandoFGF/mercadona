"""Tests del motor de recetas: validación + reintento."""
from unittest.mock import patch

import pytest

from core import recipe_engine


VALID_PLAN = {
    "days": [
        {
            "day": 1,
            "meal": "comida",
            "title": "Arroz con pollo",
            "description": "d",
            "steps": ["paso 1", "paso 2"],
            "ingredients": [{"name": "arroz", "quantity": "200g"}],
        }
    ]
}

VALID_SHOPPING = {"shopping_list": [{"name": "arroz", "quantity": "200g"}]}


def test_generate_meal_plan_valid_first_try():
    with patch("core.recipe_engine.gemini_client.generate_json", return_value=VALID_PLAN) as m:
        plan = recipe_engine.generate_meal_plan("hola")
    assert plan == VALID_PLAN
    m.assert_called_once()


def test_generate_meal_plan_retries_on_bad_json():
    bad = {"recipes": []}  # no tiene 'days'
    with patch("core.recipe_engine.gemini_client.generate_json", side_effect=[bad, VALID_PLAN]) as m:
        plan = recipe_engine.generate_meal_plan("hola")
    assert plan == VALID_PLAN
    assert m.call_count == 2


def test_generate_meal_plan_raises_after_two_bad():
    with patch("core.recipe_engine.gemini_client.generate_json", side_effect=[{"x": 1}, {"y": 2}]):
        with pytest.raises(ValueError):
            recipe_engine.generate_meal_plan("hola")


def test_consolidate_retries_on_bad_json():
    bad = {"items": []}
    with patch("core.recipe_engine.gemini_client.generate_json", side_effect=[bad, VALID_SHOPPING]) as m:
        out = recipe_engine.consolidate_shopping_list([])
    assert out == VALID_SHOPPING["shopping_list"]
    assert m.call_count == 2


def test_restrictions_appear_in_prompt():
    captured = {}
    real_call = recipe_engine.gemini_client.generate_json

    def spy(prompt, system=None):
        captured["prompt"] = prompt
        captured["system"] = system
        return VALID_PLAN

    with patch("core.recipe_engine.gemini_client.generate_json", side_effect=spy):
        recipe_engine.generate_meal_plan("hola", restrictions=["vegano", "sin_gluten"])
    assert "vegano" in captured["prompt"].lower()
    assert "sin gluten" in captured["prompt"].lower()


def test_dietary_block_empty_when_no_restrictions():
    captured = {}

    def spy(prompt, system=None):
        captured["prompt"] = prompt
        return VALID_PLAN

    with patch("core.recipe_engine.gemini_client.generate_json", side_effect=spy):
        recipe_engine.generate_meal_plan("hola", restrictions=[])
    assert "RESTRICCIONES" not in captured["prompt"]
