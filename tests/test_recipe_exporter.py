"""Tests del exportador de recetas a Markdown."""
from core.recipe_exporter import render_recipes_markdown


PLAN = {
    "days": [
        {
            "day": 1,
            "meal": "comida",
            "title": "Arroz con pollo",
            "description": "Receta sencilla de la abuela.",
            "steps": ["Sofreír el pollo", "Añadir el arroz", "Cocer 20 min"],
            "ingredients": [
                {"name": "arroz redondo", "quantity": "200g"},
                {"name": "pechuga de pollo", "quantity": "300g"},
            ],
        },
        {
            "day": 2,
            "meal": "cena",
            "title": "Ensalada rápida",
            "description": "",
            "steps": [],
            "ingredients": [{"name": "lechuga", "quantity": "1 ud"}],
        },
    ]
}


def test_renders_title_and_prompt():
    md = render_recipes_markdown(PLAN, title="Mi plan", prompt="bajo en colesterol")
    assert "# 🧠 Mi plan" in md
    assert "bajo en colesterol" in md


def test_renders_all_days():
    md = render_recipes_markdown(PLAN)
    assert "## Día 1" in md
    assert "## Día 2" in md
    assert "Arroz con pollo" in md
    assert "Ensalada rápida" in md


def test_renders_ingredients_with_qty():
    md = render_recipes_markdown(PLAN)
    assert "**arroz redondo** — 200g" in md
    assert "**pechuga de pollo** — 300g" in md


def test_renders_steps_numbered():
    md = render_recipes_markdown(PLAN)
    assert "1. sofreír el pollo" in md.lower() or "1. Sofreír el pollo" in md


def test_empty_day_steps_omitted():
    md = render_recipes_markdown(PLAN)
    # El día 2 no tiene steps, no debe haber '### Pasos' seguido de lista vacía
    assert "Ensalada" in md


def test_empty_plan_message():
    md = render_recipes_markdown({"days": []})
    assert "sin recetas" in md.lower()


def test_meal_appears_uppercase():
    md = render_recipes_markdown(PLAN)
    assert "COMIDA" in md
    assert "CENA" in md
