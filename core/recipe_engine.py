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


def _recipe_prompt(
    user_request: str,
    days: int,
    servings: int,
    restrictions: list[str] | None = None,
    personas: int = 1,
    difficulty: str = "cualquiera",
) -> str:
    dietary = _dietary_block(restrictions or [])
    diff_instruction = {
        "facil": "Todas las recetas deben ser de dificultad FÁCIL (≤20 min, pocos pasos, sin técnicas avanzadas).",
        "media": "Todas las recetas deben ser de dificultad MEDIA (~30 min, sin técnicas muy avanzadas).",
        "elaborada": "Las recetas pueden ser ELABORADAS (≥45 min, técnicas avanzadas permitidas).",
        "cualquiera": "Varía la dificultad a lo largo de la semana (fácil entre semana, más elaborada el finde).",
    }.get(difficulty, "")
    personas_clause = (
        f"El plan es para {personas} persona(s). Ajusta las cantidades al número de comensales."
        if personas > 1
        else "El plan es para 1 persona."
    )
    return f"""
Petición del usuario: "{user_request}"

Necesito un plan de {days} día(s), cada día con DOS recetas: una COMIDA (mediodía) y una CENA (noche).
Cantidades para {servings} raciones por receta ({personas} persona(s)).
{personas_clause}

{dietary}
{diff_instruction}

Devuelve estrictamente este JSON:
{{
  "days": [
    {{
      "day": 1,
      "weekday": "lunes",
      "meals": [
        {{
          "meal": "comida",
          "title": "Nombre de la receta de comida",
          "description": "Breve descripción en 1 línea",
          "difficulty": "facil|media|elaborada",
          "prep_minutes": 20,
          "steps": ["paso 1", "paso 2", "..."],
          "ingredients": [
            {{"name": "tomate triturado", "quantity": "200g"}},
            {{"name": "aceite de oliva virgen extra", "quantity": "30ml"}}
          ]
        }},
        {{
          "meal": "cena",
          "title": "Nombre de la receta de cena",
          "description": "Breve descripción en 1 línea",
          "difficulty": "facil|media|elaborada",
          "prep_minutes": 15,
          "steps": ["paso 1", "paso 2", "..."],
          "ingredients": [
            {{"name": "lechuga", "quantity": "1 unidad"}},
            {{"name": "atún en conserva", "quantity": "2 latas"}}
          ]
        }}
      ]
    }}
  ]
}}

Reglas:
- EXACTAMENTE {days} objetos en "days", uno por día (1 a {days}).
- Cada día tiene EXACTAMENTE 2 entradas en "meals": una con "meal":"comida" y otra con "meal":"cena" (en ese orden).
- "weekday" en minúsculas: lunes, martes, miércoles, jueves, viernes, sábado, domingo.
- Ingredientes con nombres reconocibles en un supermercado Mercadona (ej: "pechuga de pollo", "arroz redondo", "tomate triturado", "aceite de oliva virgen extra").
- Cantidades realistas para {servings} raciones por receta ({personas} persona(s)).
- {diff_instruction}
- "steps" entre 3 y 7 pasos cortos.
- Varía proteínas, verduras y cereales a lo largo de la semana; no repitas la misma proteína tres días seguidos.
- Si la petición menciona colesterol, calorías, vegetariano, sin gluten, ligero, fresco, verano, etc., respétalo.
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


def generate_meal_plan(
    user_request: str,
    days: int = 1,
    servings: int = 2,
    restrictions: list[str] | None = None,
    personas: int = 1,
    difficulty: str = "cualquiera",
) -> dict[str, Any]:
    """Genera un plan de recetas estructurado a partir de una petición libre."""
    servings = max(1, servings) if servings else max(1, personas * 2)
    prompt = _recipe_prompt(
        user_request, days, servings,
        restrictions=restrictions or [],
        personas=personas, difficulty=difficulty,
    )
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
