"""Tests del exportador de recetas a Markdown."""
from core.recipe_exporter import render_recipes_markdown


PLAN_V2 = {
    "days": [
        {
            "day": 1, "weekday": "lunes",
            "meals": [
                {
                    "meal": "comida", "title": "Arroz con pollo",
                    "description": "Receta sencilla.", "difficulty": "facil", "prep_minutes": 30,
                    "steps": ["Sofreír el pollo", "Añadir el arroz", "Cocer 20 min"],
                    "ingredients": [
                        {"name": "arroz redondo", "quantity": "200g"},
                        {"name": "pechuga de pollo", "quantity": "300g"},
                    ],
                },
                {
                    "meal": "cena", "title": "Ensalada rápida",
                    "description": "", "difficulty": "facil", "prep_minutes": 10,
                    "steps": [],
                    "ingredients": [{"name": "lechuga", "quantity": "1 ud"}],
                },
            ],
        },
    ]
}


def test_renders_title_and_prompt():
    md = render_recipes_markdown(PLAN_V2, title="Mi plan", prompt="bajo en colesterol")
    assert "# 🧠 Mi plan" in md
    assert "bajo en colesterol" in md


def test_renders_day_with_weekday():
    md = render_recipes_markdown(PLAN_V2)
    assert "## Día 1 — Lunes" in md
    assert "Arroz con pollo" in md
    assert "Ensalada rápida" in md


def test_renders_comida_and_cena():
    md = render_recipes_markdown(PLAN_V2)
    assert "COMIDA" in md
    assert "CENA" in md


def test_renders_ingredients_with_qty():
    md = render_recipes_markdown(PLAN_V2)
    assert "**arroz redondo** — 200g" in md
    assert "**pechuga de pollo** — 300g" in md


def test_renders_steps_numbered():
    md = render_recipes_markdown(PLAN_V2)
    assert "1. sofreír el pollo" in md.lower() or "1. Sofreír el pollo" in md


def test_renders_difficulty_and_time():
    md = render_recipes_markdown(PLAN_V2)
    assert "dificultad: facil" in md
    assert "~30 min" in md


def test_legacy_flat_structure_still_renders():
    plan_legacy = {
        "days": [
            {
                "day": 1, "meal": "comida", "title": "Legacy",
                "steps": ["paso"], "ingredients": [{"name": "x", "quantity": "1g"}],
            }
        ]
    }
    md = render_recipes_markdown(plan_legacy)
    assert "Legacy" in md
    assert "## Día 1" in md


def test_empty_plan_message():
    md = render_recipes_markdown({"days": []})
    assert "sin recetas" in md.lower()
