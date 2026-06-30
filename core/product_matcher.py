"""
Matching ingrediente → producto real de Mercadona.

Estrategia en 3 niveles:
1. Búsqueda directa con el nombre del ingrediente.
2. Si falla, fuzzy match sobre los hits (rapidfuzz si está disponible, sino difflib).
3. Fallback: devuelve el primer hit de la búsqueda aunque el score sea bajo.
"""
from difflib import SequenceMatcher
from typing import Any

from adapters import mercadona_cli

try:
    from rapidfuzz import fuzz  # type: ignore
    _HAS_RAPIDFUZZ = True
except Exception:
    _HAS_RAPIDFUZZ = False


def _score(a: str, b: str) -> float:
    a = a.lower().strip()
    b = b.lower().strip()
    if _HAS_RAPIDFUZZ:
        return max(fuzz.token_set_ratio(a, b), fuzz.WRatio(a, b)) / 100.0
    return SequenceMatcher(None, a, b).ratio()


def _best_hit(ingredient: str, hits: list[dict[str, Any]], min_score: float = 0.45) -> dict[str, Any] | None:
    if not hits:
        return None
    scored = []
    for h in hits:
        name = h.get("display_name") or h.get("name") or h.get("product_name") or ""
        scored.append((_score(ingredient, name), h))
    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_hit = scored[0]
    if best_score >= min_score:
        return best_hit
    return None


def match(ingredient: str, limit: int = 5, fresh: bool = False) -> dict[str, Any] | None:
    """
    Devuelve el mejor producto de Mercadona para un ingrediente.
    Estructura normalizada:
      {"id": ..., "name": ..., "price": float, "unit_price": float|None, "raw": ...}
    """
    hits = mercadona_cli.search(ingredient, limit=limit, fresh=fresh)
    if not hits:
        return None

    best = _best_hit(ingredient, hits) or hits[0]

    price = best.get("price_instructions", {}).get("unit_price") if isinstance(
        best.get("price_instructions"), dict
    ) else None
    if price is None:
        price = best.get("unit_price") or best.get("price") or 0.0

    name = best.get("display_name") or best.get("name") or best.get("product_name") or ingredient
    pid = best.get("id") or best.get("product_id")

    return {
        "id": pid,
        "name": name,
        "price": float(price or 0.0),
        "unit_price": best.get("reference_price") or best.get("unit_price_ref"),
        "raw": best,
    }


def match_many(ingredients: list[str], fresh: bool = True) -> list[dict[str, Any]]:
    """Empareja varios ingredientes, devolviendo la lista de productos resueltos."""
    return [match(ing, fresh=fresh) or {"id": None, "name": ing, "price": 0.0, "raw": None}
            for ing in ingredients]
