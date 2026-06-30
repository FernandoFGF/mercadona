"""
Matching semántico ingrediente → producto con embeddings de Gemini.

Pipeline:
1. Embedding del término de búsqueda (Gemini text-embedding-004).
2. Cache local en data/embeddings.npz (término → vector).
3. Comparación cosine contra los nombres de los productos devueltos
   por mercadona_cli.search().
4. Si el mejor score < umbral, fallback al fuzzy matching clásico.

La API key de Gemini es necesaria. Sin ella, el módulo se comporta
como un no-op y `match_semantic` devuelve None.
"""
import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
import requests

import config


logger = logging.getLogger(__name__)


_EMBED_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent"
_EMBED_DIM = 3072  # gemini-embedding-001 (legacy: 768 con text-embedding-004)
_CACHE_PATH = config.DATA_DIR / "embeddings.npz"
_TTL_SECONDS = 7 * 24 * 3600
_MIN_SCORE = 0.55


def _is_enabled() -> bool:
    return bool(config.GEMINI_API_KEY)


def _load_index() -> tuple[list[str], np.ndarray | None]:
    if not _CACHE_PATH.exists():
        return [], None
    try:
        with np.load(_CACHE_PATH, allow_pickle=False) as data:
            terms = [str(t) for t in data["terms"].tolist()]
            vecs = data["vectors"]
            ts = float(data["ts"].item()) if "ts" in data.files else 0.0
        if time.time() - ts > _TTL_SECONDS:
            return [], None
        return terms, vecs
    except (OSError, KeyError, ValueError):
        return [], None


def _save_index(terms: list[str], vecs: np.ndarray) -> None:
    try:
        ts = np.array([time.time()], dtype=np.float64)
        np.savez(
            _CACHE_PATH,
            terms=np.array(terms, dtype=object),
            vectors=vecs,
            ts=ts,
        )
    except OSError as e:
        logger.warning("No se pudo guardar embeddings.npz: %s", e)


def _embed_one(text: str) -> np.ndarray | None:
    if not _is_enabled():
        return None
    body = {
        "model": "models/gemini-embedding-001",
        "content": {"parts": [{"text": text}]},
        "taskType": "RETRIEVAL_QUERY",
    }
    url = _EMBED_URL + f"?key={config.GEMINI_API_KEY}"
    try:
        resp = requests.post(url, json=body, timeout=30)
    except requests.RequestException as e:
        logger.warning("Embedding request error: %s", e)
        return None
    if resp.status_code != 200:
        logger.warning("Embedding HTTP %d: %s", resp.status_code, resp.text[:200])
        return None
    try:
        values = resp.json()["embedding"]["values"]
    except (KeyError, ValueError) as e:
        logger.warning("Embedding respuesta inesperada: %s", e)
        return None
    return np.array(values, dtype=np.float32)


def _get_or_compute_embedding(term: str) -> np.ndarray | None:
    terms, vecs = _load_index()
    key = term.lower().strip()
    if vecs is not None and key in terms:
        i = terms.index(key)
        return vecs[i]
    vec = _embed_one(term)
    if vec is None:
        return None
    if vecs is None:
        terms = [key]
        vecs = vec.reshape(1, -1)
    else:
        if key in terms:
            i = terms.index(key)
            vecs[i] = vec
        else:
            terms.append(key)
            vecs = np.vstack([vecs, vec.reshape(1, -1)])
    _save_index(terms, vecs)
    return vec


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _normalize_product_name(p: dict[str, Any]) -> str:
    return (p.get("display_name") or p.get("name") or p.get("product_name") or "").strip()


def _embed_products(products: list[dict[str, Any]]) -> dict[int, np.ndarray]:
    """Embed nombres de producto cacheando en el índice."""
    out: dict[int, np.ndarray] = {}
    for p in products:
        pid = p.get("id")
        name = _normalize_product_name(p)
        if pid is None or not name:
            continue
        vec = _get_or_compute_embedding(name)
        if vec is not None:
            out[pid] = vec
    return out


def match_semantic(
    ingredient: str,
    hits: list[dict[str, Any]],
    min_score: float = _MIN_SCORE,
) -> dict[str, Any] | None:
    """
    Devuelve el producto de `hits` más cercano semánticamente al ingrediente.
    Devuelve None si no hay API key, no se puede embeber, o todos los scores
    están por debajo del umbral.
    """
    if not hits or not _is_enabled():
        return None
    ing_vec = _get_or_compute_embedding(ingredient)
    if ing_vec is None:
        return None
    prod_vecs = _embed_products(hits)
    if not prod_vecs:
        return None

    best_pid, best_score = None, -1.0
    for p in hits:
        pid = p.get("id")
        if pid in prod_vecs:
            s = _cosine(ing_vec, prod_vecs[pid])
            if s > best_score:
                best_score, best_pid = s, pid

    if best_pid is None or best_score < min_score:
        logger.info(
            "Semantic match: best score %.3f < %.3f for '%s'",
            best_score, min_score, ingredient,
        )
        return None
    return next((p for p in hits if p.get("id") == best_pid), None)
