"""
Matching semántico ingrediente → producto con embeddings de Gemini.

Pipeline:
1. Embedding del término de búsqueda (Gemini gemini-embedding-001).
2. Cache local en data/embeddings.npz (término → vector).
3. Comparación cosine contra los nombres de los productos devueltos
   por mercadona_cli.search().
4. Si el mejor score < umbral, fallback al fuzzy matching clásico.

La API key de Gemini es necesaria. Sin ella, el módulo se comporta
como un no-op y `match_semantic` devuelve None.

Rate limiting:
- Mínimo _MIN_INTERVAL_SECONDS entre llamadas (default 2s).
- Circuit breaker: tras _CB_FAILS errores 429 consecutivos, desactivamos
  embeddings durante _CB_COOLDOWN_SECONDS.
- Cache negativa en memoria: no reintentar el mismo término durante
  _NEG_TTL_SECONDS si ya dio 429.
"""
import logging
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np
import requests

import config
from core.settings_store import get as settings_get


logger = logging.getLogger(__name__)


_EMBED_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent"
_EMBED_DIM = 3072
_CACHE_PATH = config.DATA_DIR / "embeddings.npz"
_TTL_SECONDS = 7 * 24 * 3600
_MIN_SCORE = 0.70

# Rate limiting / circuit breaker
_MIN_INTERVAL_SECONDS = 2.0
_CB_FAILS = 3
_CB_COOLDOWN_SECONDS = 300  # 5 min sin intentar tras 3 fallos 429
_NEG_TTL_SECONDS = 3600  # 1h sin reintentar términos que dieron 429

_last_call_ts: float = 0.0
_recent_429: list[float] = []
_negative_cache: dict[str, float] = {}
_circuit_open_until: float = 0.0
_lock = threading.Lock()


def _is_enabled() -> bool:
    """Embedding solo si: hay API key + setting habilitado + circuito cerrado."""
    if not config.GEMINI_API_KEY:
        return False
    if not bool(settings_get("usar_embeddings")):
        return False
    with _lock:
        if time.time() < _circuit_open_until:
            return False
    return True


def _register_429(term_key: str) -> None:
    """Registra un 429: actualiza circuit breaker y negative cache."""
    global _circuit_open_until
    now = time.time()
    with _lock:
        _recent_429.append(now)
        # Solo nos interesan los últimos 5 minutos
        _recent_429[:] = [t for t in _recent_429 if now - t < 300]
        if len(_recent_429) >= _CB_FAILS:
            _circuit_open_until = now + _CB_COOLDOWN_SECONDS
            logger.warning(
                "Circuit breaker ABIERTO: embeddings desactivados %ds tras %d 429s",
                _CB_COOLDOWN_SECONDS, len(_recent_429),
            )
        _negative_cache[term_key] = now + _NEG_TTL_SECONDS


def _is_cached_429(term_key: str) -> bool:
    with _lock:
        until = _negative_cache.get(term_key, 0.0)
    return time.time() < until


def _wait_for_rate_limit() -> None:
    """Espera lo necesario para respetar _MIN_INTERVAL_SECONDS entre llamadas."""
    global _last_call_ts
    with _lock:
        now = time.time()
        wait = _MIN_INTERVAL_SECONDS - (now - _last_call_ts)
        if wait > 0:
            time.sleep(wait)
        _last_call_ts = time.time()


def circuit_is_open() -> bool:
    """Para diagnóstico / UI: True si el circuit breaker está abierto."""
    return time.time() < _circuit_open_until


def reset_circuit() -> None:
    """Cierra el circuit breaker manualmente. Útil desde la UI."""
    global _circuit_open_until, _recent_429
    with _lock:
        _circuit_open_until = 0.0
        _recent_429.clear()


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
    key = text.lower().strip()
    if _is_cached_429(key):
        return None
    _wait_for_rate_limit()
    body = {
        "model": "models/gemini-embedding-001",
        "content": {"parts": [{"text": text}]},
        "taskType": "RETRIEVAL_QUERY",
    }
    url = _EMBED_URL + f"?key={config.GEMINI_API_KEY}"
    try:
        resp = requests.post(url, json=body, timeout=30)
    except requests.RequestException as e:
        logger.warning("Error en petición de embedding: %s", e)
        return None
    if resp.status_code == 429:
        logger.warning("Embeddings HTTP 429 (cuota agotada, rate limit)")
        _register_429(key)
        return None
    if resp.status_code != 200:
        logger.warning("Embeddings HTTP %d: %s", resp.status_code, resp.text[:200])
        return None
    try:
        values = resp.json()["embedding"]["values"]
    except (KeyError, ValueError) as e:
        logger.warning("Embeddings respuesta inesperada: %s", e)
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
            "Match semántico: mejor score %.3f < %.3f para '%s'",
            best_score, min_score, ingredient,
        )
        return None
    return next((p for p in hits if p.get("id") == best_pid), None)
