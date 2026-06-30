"""
Motor de recetas: genera menús / recetas estructurados con Gemini
y los devuelve como dicts limpios.
"""
import json
from typing import Any

from core import gemini_client
from core.recipe_schema import MealPlan, ShoppingList


RECIPE_SYSTEM = (
    "Eres un asistente culinario español. Devuelves SIEMPRE JSON válido, "
    "sin texto extra, sin bloques de código. Usas cantidades en unidades "
    "cotidianas (g, ml, unidades). Nombras ingredientes con palabras que "
    "se encontrarían en un supermercado Mercadona español."
)


_CORRECTION_SYSTEM = (
    "Tu respuesta anterior NO se pudo parsear como JSON válido o no "
    "cumplía el esquema. Devuelve SOLO el JSON corregido, sin texto extra."
)


DIETARY_RESTRICTIONS = {
    "vegetariano": "No incluyas carne, pescado ni marisco. Huevos y lácteos sí.",
    "vegano": "No incluyas productos de origen animal (carne, pescado, huevos, lácteos, miel).",
    "sin_gluten": "No incluyas trigo, cebada, centeno ni derivados. Evita salsas y procesados con gluten.",
    "sin_lactosa": "No incluyas leche, yogur, queso, mantequilla ni derivados lácteos.",
    "bajo_sodio": "Reduce la sal y evita embutidos, conservas, salsas industriales y quesos curados.",
}


def _dietary_block(restrictions: list[str]) -> str:
    if not restrictions:
        return ""
    lines = ["RESTRICCIONES DIETÉTICAS (obligatorias):"]
    for r in restrictions:
        if r in DIETARY_RESTRICTIONS:
            lines.append(f"- {r.upper().replace('_', ' ')}: {DIETARY_RESTRICTIONS[r]}")
    return "\n".join(lines)


def _recipe_prompt(user_request: str, days: int, servings: int, restrictions: list[str] | None = None) -> str:
    dietary = _dietary_block(restrictions or [])
    return f"""
Petición del usuario: "{user_request}"

Necesito un plan de {days} día(s) con {servings} raciones por receta.
Para CADA día genera UNA receta principal (comida o cena, tú decides).

{dietary}

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
- Si la petición menciona colesterol, calorías, etc., respétalo.
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


def generate_meal_plan(user_request: str, days: int = 1, servings: int = 2, restrictions: list[str] | None = None) -> dict[str, Any]:
    """Genera un plan de recetas estructurado a partir de una petición libre."""
    prompt = _recipe_prompt(user_request, days, servings, restrictions=restrictions or [])
    try:
        data = gemini_client.generate_json(prompt, system=RECIPE_SYSTEM)
        MealPlan.from_dict(data)
        return data
    except (ValueError, json.JSONDecodeError):
        correction = (
            "Tu última respuesta no encajaba con el esquema esperado. "
            "Devuelve únicamente el JSON válido, respetando exactamente "
            "la estructura indicada en el prompt original.\n\n"
            f"PROMPT ORIGINAL:\n{prompt}"
        )
        data = gemini_client.generate_json(correction, system=_CORRECTION_SYSTEM)
        MealPlan.from_dict(data)
        return data


def consolidate_shopping_list(recipes: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Pide a Gemini que consolide ingredientes de varias recetas en una lista de la compra."""
    prompt = _shopping_list_prompt(recipes)
    try:
        data = gemini_client.generate_json(prompt, system=RECIPE_SYSTEM)
        ShoppingList.from_dict(data)
        return data.get("shopping_list", [])
    except (ValueError, json.JSONDecodeError):
        correction = (
            "Tu última respuesta no encajaba con el esquema. "
            "Devuelve únicamente el JSON válido con la clave 'shopping_list'.\n\n"
            f"PROMPT ORIGINAL:\n{prompt}"
        )
        data = gemini_client.generate_json(correction, system=_CORRECTION_SYSTEM)
        ShoppingList.from_dict(data)
        return data.get("shopping_list", [])
