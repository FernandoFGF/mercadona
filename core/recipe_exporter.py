"""
Serializa un plan de recetas (estructura devuelta por Gemini) a Markdown.
"""
from datetime import datetime
from typing import Any


def _ingredients_section(ings: list[dict[str, Any]]) -> str:
    if not ings:
        return ""
    lines = ["### Ingredientes", ""]
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
    lines = ["### Pasos", ""]
    for i, s in enumerate(steps, 1):
        lines.append(f"{i}. {s}")
    return "\n".join(lines)


def render_recipes_markdown(
    plan: dict[str, Any],
    title: str = "Plan de recetas",
    prompt: str | None = None,
) -> str:
    """
    Renderiza un plan completo (con clave 'days') a Markdown.

    Ejemplo de estructura esperada:
        {"days": [{"day": 1, "meal": "comida", "title": "...",
                   "description": "...", "steps": [...], "ingredients": [...]}]}
    """
    days = plan.get("days", [])
    out = [f"# 🧠 {title}", ""]
    if prompt:
        out.append(f"> Petición: _{prompt}_")
        out.append("")
    out.append(f"_Generado el {datetime.now().strftime('%Y-%m-%d %H:%M')}._")
    out.append("")

    for r in days:
        day = r.get("day", "?")
        meal = (r.get("meal") or "").upper()
        rec_title = r.get("title", "Receta sin título")
        meal_str = f" · {meal}" if meal else ""
        out.append(f"## Día {day}{meal_str} — {rec_title}")
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
        out.append("---")
        out.append("")

    if not days:
        out.append("_(sin recetas)_")
    return "\n".join(out)
