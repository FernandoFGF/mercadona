"""
Serializa un plan de recetas (estructura devuelta por Gemini) a Markdown.

Soporta dos formatos:
  1. Nuevo (con comidas y cenas por día):
     {"days": [{"day": 1, "weekday": "lunes",
                "meals": [{"meal": "comida", "title": "...", ...},
                          {"meal": "cena",   "title": "...", ...}]}]}
  2. Antiguo (plano, una receta por entrada): fallback automático.
"""
from datetime import datetime
from typing import Any


def _ingredients_section(ings: list[dict[str, Any]]) -> str:
    if not ings:
        return ""
    lines = ["**Ingredientes:**", ""]
    for ing in ings:
        name = ing.get("name", "").strip()
        qty = ing.get("quantity", "").strip()
        if name and qty:
            lines.append(f"- **{name}** — {qty}")
        elif name:
            lines.append(f"- **{name}**")
    return "\n".join(lines)


def _steps_section(steps: list[str]) -> str:
    if not steps:
        return ""
    lines = ["**Pasos:**", ""]
    for i, s in enumerate(steps, 1):
        lines.append(f"{i}. {s}")
    return "\n".join(lines)


def _meal_section(r: dict[str, Any]) -> list[str]:
    out: list[str] = []
    meal = (r.get("meal") or "").upper()
    rec_title = r.get("title", "Receta sin título")
    meal_str = f" — {meal}" if meal else ""
    difficulty = r.get("difficulty", "")
    prep = r.get("prep_minutes", 0)
    meta_bits = []
    if difficulty:
        meta_bits.append(f"dificultad: {difficulty}")
    if prep:
        meta_bits.append(f"~{prep} min")
    out.append(f"### {rec_title}{meal_str}")
    out.append("")
    if meta_bits:
        out.append(f"_{'  ·  '.join(meta_bits)}_")
        out.append("")
    if r.get("description"):
        out.append(r["description"])
        out.append("")
    ings = _ingredients_section(r.get("ingredients", []))
    if ings:
        out.append(ings)
        out.append("")
    steps = _steps_section(r.get("steps", []))
    if steps:
        out.append(steps)
        out.append("")
    return out


def render_recipes_markdown(
    plan: dict[str, Any],
    title: str = "Plan de recetas",
    prompt: str | None = None,
) -> str:
    days = plan.get("days", [])
    out = [f"# 🧠 {title}", ""]
    if prompt:
        out.append(f"> Petición: _{prompt}_")
        out.append("")
    out.append(f"_Generado el {datetime.now().strftime('%Y-%m-%d %H:%M')}._")
    out.append("")

    for d in days:
        day = d.get("day", "?")
        weekday = d.get("weekday", "")
        title_str = f"## Día {day}" + (f" — {weekday.capitalize()}" if weekday else "")
        out.append(title_str)
        out.append("")
        meals = d.get("meals")
        if meals:
            for r in meals:
                out.extend(_meal_section(r))
        elif {"title", "ingredients"}.intersection(d.keys()):
            # compat: estructura antigua plana
            out.extend(_meal_section(d))
        out.append("---")
        out.append("")

    if not days:
        out.append("_(sin recetas)_")
    return "\n".join(out)
