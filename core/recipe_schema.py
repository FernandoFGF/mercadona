"""
Esquema de las recetas devueltas por Gemini. Validación con dataclasses.
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Ingredient:
    name: str
    quantity: str = ""

    @classmethod
    def from_dict(cls, d: Any) -> "Ingredient":
        if not isinstance(d, dict):
            raise ValueError(f"ingredient no es dict: {d!r}")
        name = d.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"ingredient sin 'name' válido: {d!r}")
        qty = d.get("quantity", "")
        if not isinstance(qty, str):
            qty = str(qty)
        return cls(name=name.strip(), quantity=qty.strip())


@dataclass
class Recipe:
    day: int
    meal: str
    title: str
    description: str
    steps: list[str] = field(default_factory=list)
    ingredients: list[Ingredient] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: Any) -> "Recipe":
        if not isinstance(d, dict):
            raise ValueError(f"recipe no es dict: {d!r}")
        try:
            day = int(d.get("day", 0))
        except (TypeError, ValueError):
            raise ValueError(f"recipe.day inválido: {d.get('day')!r}")
        meal = str(d.get("meal", "")).strip().lower() or "comida"
        if meal not in ("comida", "cena"):
            meal = "comida"
        title = str(d.get("title", "")).strip() or "Receta sin título"
        description = str(d.get("description", "")).strip()
        steps_raw = d.get("steps", [])
        if not isinstance(steps_raw, list):
            steps_raw = []
        steps = [str(s).strip() for s in steps_raw if str(s).strip()]
        ings_raw = d.get("ingredients", [])
        if not isinstance(ings_raw, list):
            ings_raw = []
        ings = [Ingredient.from_dict(i) for i in ings_raw if isinstance(i, dict)]
        return cls(
            day=day, meal=meal, title=title, description=description,
            steps=steps, ingredients=ings,
        )


@dataclass
class MealPlan:
    days: list[Recipe] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: Any) -> "MealPlan":
        if not isinstance(d, dict):
            raise ValueError(f"plan no es dict: {d!r}")
        if "days" not in d:
            raise ValueError(f"plan sin clave 'days': {list(d.keys())}")
        raw_days = d["days"]
        if not isinstance(raw_days, list):
            raise ValueError(f"plan.days no es lista: {raw_days!r}")
        return cls(days=[Recipe.from_dict(r) for r in raw_days if isinstance(r, dict)])

    def ingredient_names(self) -> list[str]:
        out: list[str] = []
        for r in self.days:
            for ing in r.ingredients:
                out.append(ing.name)
        return out


@dataclass
class ShoppingItem:
    name: str
    quantity: str = ""

    @classmethod
    def from_dict(cls, d: Any) -> "ShoppingItem":
        if not isinstance(d, dict):
            raise ValueError(f"shopping item no es dict: {d!r}")
        name = d.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"shopping item sin 'name' válido: {d!r}")
        return cls(name=name.strip(), quantity=str(d.get("quantity", "")).strip())


@dataclass
class ShoppingList:
    items: list[ShoppingItem] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: Any) -> "ShoppingList":
        if not isinstance(d, dict):
            raise ValueError(f"shopping list no es dict: {d!r}")
        if "shopping_list" not in d:
            raise ValueError(f"shopping_list sin clave 'shopping_list': {list(d.keys())}")
        raw = d["shopping_list"]
        if not isinstance(raw, list):
            raise ValueError(f"shopping_list no es lista: {raw!r}")
        return cls(items=[ShoppingItem.from_dict(i) for i in raw if isinstance(i, dict)])

    def names(self) -> list[str]:
        return [i.name for i in self.items]
