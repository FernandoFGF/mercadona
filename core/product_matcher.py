"""
Matching ingrediente → producto real de Mercadona.

Estrategia en 4 niveles:
1. Búsqueda directa con el nombre del ingrediente.
2. Matching semántico con Gemini embeddings (si hay API key).
3. Fuzzy match sobre los hits (rapidfuzz si está disponible, sino difflib).
4. Fallback: devuelve el primer hit de la búsqueda aunque el score sea bajo.
"""
import re
from difflib import SequenceMatcher
from typing import Any

from adapters import mercadona_cli
from core import semantic_matcher

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


def _best_hit(ingredient: str, hits: list[dict[str, Any]], min_score: float = 0.65) -> dict[str, Any] | None:
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


def _normalize(best: dict[str, Any], ingredient: str) -> dict[str, Any]:
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
        "match_kind": "unknown",
    }


def match(ingredient: str, limit: int = 5, fresh: bool = False) -> dict[str, Any] | None:
    """
    Devuelve el mejor producto de Mercadona para un ingrediente.
    Estructura normalizada:
      {"id": ..., "name": ..., "price": float, "unit_price": float|None,
       "raw": ..., "match_kind": "semantic"|"fuzzy"|"fallback"}
    """
    hits = mercadona_cli.search(ingredient, limit=limit, fresh=fresh)
    if not hits:
        return None

    best = semantic_matcher.match_semantic(ingredient, hits)
    if best is not None:
        result = _normalize(best, ingredient)
        result["match_kind"] = "semantic"
        return result

    best = _best_hit(ingredient, hits) or hits[0]
    result = _normalize(best, ingredient)
    result["match_kind"] = "fuzzy" if _best_hit(ingredient, hits) else "fallback"
    return result


def match_many(ingredients: list[str], fresh: bool = True) -> list[dict[str, Any]]:
    """Empareja varios ingredientes, devolviendo la lista de productos resueltos."""
    return [match(ing, fresh=fresh) or {"id": None, "name": ing, "price": 0.0, "raw": None, "match_kind": "none"}
            for ing in ingredients]


def _core_name(name: str) -> str:
    """Normaliza un nombre de producto a su 'core' (sin marca, sin adjetivos).

    Sirve para detectar duplicados: 'Vinagre de manzana Hacendado' y
    'Vinagre balsamico de Modena Hacendado' comparten 'vinagre'.
    """
    s = name.lower()
    # Quitar marca tipica de Mercadona
    for brand in ("hacendado", "deluxe", "bosque verde", "casa juncal",
                  "soler de cabras", "anitin"):
        s = s.replace(brand, "")
    # Quitar adjetivos tipicos y palabras de relleno
    stop = (
        "de", "el", "la", "los", "las", "con", "sin", "para", "al",
        "reserva", "ecologico", "ecologica", "bio", "light", "0%",
        "natural", "fresco", "fresca", "entero", "entera", "troceado",
        "rallado", "lavado", "lavada", "pelado", "pelada", "cocido",
        "cocida", "en", "conserva", "lonchas", "rodajas", "dientes",
        "extra", "virgen", "molido", "picado", "molida", "picada",
    )
    tokens = [t for t in re.split(r"[^a-z0-9]+", s) if t and t not in stop]
    return " ".join(sorted(tokens))


def dedupe_by_core(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Consolida productos cuyo core normalizado es identico o muy similar.

    Si dos productos matcheados tienen el mismo core ('vinagre' en
    'Vinagre de manzana' y 'Vinagre balsamico'), nos quedamos con el
    primero (que suele ser el que mayor cantidad lleva).
    """
    if not products:
        return products
    seen: dict[str, dict[str, Any]] = {}
    out: list[dict[str, Any]] = []
    for p in products:
        name = p.get("name") or ""
        core = _core_name(name)
        if not core:
            out.append(p)
            continue
        if core in seen:
            continue
        # Buscar core parecido entre los ya vistos (Levenshtein-like)
        match_key = None
        for existing_core in seen:
            if existing_core == core:
                match_key = existing_core
                break
            # Si comparten el primer token significativo, son el mismo producto
            e_tokens = set(existing_core.split())
            c_tokens = set(core.split())
            if e_tokens and c_tokens and (e_tokens & c_tokens):
                common = e_tokens & c_tokens
                if len(common) >= max(1, min(len(e_tokens), len(c_tokens)) // 2):
                    match_key = existing_core
                    break
        if match_key:
            continue
        seen[core] = p
        out.append(p)
    return out
