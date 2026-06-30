"""Tests del esquema de recetas."""
import pytest

from core.recipe_schema import (
    Ingredient, Recipe, MealPlan, ShoppingItem, ShoppingList,
)


def test_ingredient_from_dict():
    ing = Ingredient.from_dict({"name": "arroz", "quantity": "200g"})
    assert ing.name == "arroz"
    assert ing.quantity == "200g"


def test_ingredient_missing_name_raises():
    with pytest.raises(ValueError):
        Ingredient.from_dict({"name": ""})
    with pytest.raises(ValueError):
        Ingredient.from_dict({"quantity": "200g"})
    with pytest.raises(ValueError):
        Ingredient.from_dict("not a dict")


def test_recipe_normalizes_meal():
    r = Recipe.from_dict({"day": 1, "meal": "COMIDA", "title": "T", "description": "d"})
    assert r.meal == "comida"


def test_recipe_invalid_meal_defaults():
    r = Recipe.from_dict({"day": 1, "meal": "postre", "title": "T"})
    assert r.meal == "comida"


def test_recipe_filters_empty_steps():
    r = Recipe.from_dict({"day": 1, "title": "T", "steps": ["a", "", "  ", "b"]})
    assert r.steps == ["a", "b"]


def test_meal_plan_ingredient_names():
    plan = MealPlan.from_dict({
        "days": [
            {"day": 1, "title": "A", "ingredients": [{"name": "arroz"}, {"name": "pollo"}]},
            {"day": 2, "title": "B", "ingredients": [{"name": "leche"}]},
        ]
    })
    assert plan.ingredient_names() == ["arroz", "pollo", "leche"]


def test_meal_plan_no_days_key():
    with pytest.raises(ValueError):
        MealPlan.from_dict({"recipes": []})


def test_meal_plan_empty_days_ok():
    plan = MealPlan.from_dict({"days": []})
    assert plan.days == []


def test_shopping_list_from_dict():
    sl = ShoppingList.from_dict({"shopping_list": [{"name": "arroz", "quantity": "200g"}]})
    assert len(sl.items) == 1
    assert sl.names() == ["arroz"]


def test_shopping_list_bad_structure():
    with pytest.raises(ValueError):
        ShoppingList.from_dict({"shopping_list": "not a list"})
    with pytest.raises(ValueError):
        ShoppingList.from_dict({"items": []})  # clave incorrecta
