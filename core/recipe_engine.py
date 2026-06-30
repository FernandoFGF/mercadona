"""
Motor de recetas: genera menús / recetas estructurados con Gemini
y los devuelve como dicts limpios.
"""
import json
from typing import Any

from core import gemini_client


RECIPE_SYSTEM = (
    "Eres un asistente culinario español. Devuelves SIEMPRE JSON válido, "
    "sin texto extra, sin bloques de código. Usas cantidades en unidades "
    "cotidianas (g, ml, unidades). Nombras ingredientes con palabras que "
    "se encontrarían en un supermercado Mercadona español."
)


def _recipe_prompt(user_request: str, days: int, servings: int) -> str:
    return f"""
Petición del usuario: "{user_request}"

Necesito un plan de {days} día(s) con {servings} raciones por receta.
Para CADA día genera UNA receta principal (comida o cena, tú decides).

Devuelve estrictamente este JSON:
{{
  "days": [
    {{
      "day": 1,
      "meal": "comida|cena",
      "title": "Nombre de la receta",
      "description": "Breve descripción en 1 línea",
      "steps": ["paso 1", "paso 2", "..."],
      "ingredients": [
        {{"name": "tomate triturado", "quantity": "200g"}},
        {{"name": "aceite de oliva virgen extra", "quantity": "30ml"}}
      ]
    }}
  ]
}}

Reglas:
- Ingredientes con nombres reconocibles en un supermercado (ej: "pechuga de pollo", "arroz redondo", "tomate triturado", "aceite de oliva virgen extra").
- Cantidades realistas para {servings} raciones.
- Si la petición menciona colesterol, calorías, vegetariano, etc., respétalo.
- "steps" entre 3 y 7 pasos cortos.
""".strip()


def _shopping_list_prompt(recipes: list[dict[str, Any]]) -> str:
    ingredients_flat = []
    for r in recipes:
        for ing in r.get("ingredients", []):
            ingredients_flat.append(ing)
    return f"""
A partir de esta lista de ingredientes de varias recetas, genera una LISTA DE LA COMPRA
consolidada y agrupada por producto compatible. Usa nombres de supermercado Mercadona.

Ingredientes:
{json.dumps(ingredients_flat, ensure_ascii=False, indent=2)}

Devuelve estrictamente:
{{
  "shopping_list": [
    {{"name": "tomate triturado Hacendado", "quantity": "400g"}},
    {{"name": "pechuga de pollo", "quantity": "600g"}}
  ]
}}

Reglas:
- Suma cantidades si el mismo producto aparece varias veces.
- Usa nombres específicos de producto (marca Hacendado cuando sea genérico).
- No incluyas texto fuera del JSON.
""".strip()


def generate_meal_plan(user_request: str, days: int = 1, servings: int = 2) -> dict[str, Any]:
    """Genera un plan de recetas estructurado a partir de una petición libre."""
    prompt = _recipe_prompt(user_request, days, servings)
    data = gemini_client.generate_json(prompt, system=RECIPE_SYSTEM)
    if "days" not in data:
        raise ValueError(f"Gemini no devolvió 'days': {data}")
    return data


def consolidate_shopping_list(recipes: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Pide a Gemini que consolide ingredientes de varias recetas en una lista de la compra."""
    prompt = _shopping_list_prompt(recipes)
    data = gemini_client.generate_json(prompt, system=RECIPE_SYSTEM)
    return data.get("shopping_list", [])
