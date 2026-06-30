"""
Settings del usuario con override sobre variables de entorno.

Jerarquía (mayor prioridad arriba):
  1. env vars (GEMINI_MODEL, MERCADONA_WAREHOUSE, etc.) — útil para CI/dev
  2. data/settings.json — persistido por el usuario desde la UI
  3. defaults en config.py

Para usar settings desde la UI:
    from core.settings_store import get as settings_get
    settings_get("gemini_model")
"""
import json
import logging
from pathlib import Path
from typing import Any

import config


logger = logging.getLogger(__name__)


DEFAULTS = {
    "gemini_model": config.GEMINI_MODEL,
    "gemini_temperature": 0.6,
    "mercadona_warehouse": config.MERCADONA_WAREHOUSE,
    "mercadona_max_eur": config.MERCADONA_MAX_EUR,
    "appearance_mode": "dark",  # dark | light
    "usar_embeddings": True,  # matching semántico; desactivar si da 429
}


def _path() -> Path:
    return config.DATA_DIR / "settings.json"


def load() -> dict[str, Any]:
    p = _path()
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("settings.json no legible: %s", e)
    return {}


def save(values: dict[str, Any]) -> None:
    try:
        # Solo guardamos claves conocidas, no secretos
        clean = {k: v for k, v in values.items() if k in DEFAULTS}
        _path().write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as e:
        logger.warning("No se pudo guardar settings.json: %s", e)


def get(key: str) -> Any:
    """Lee un setting: env > settings.json > default.

    Las env vars tienen la prioridad más alta para permitir override en CI/dev.
    """
    if key not in DEFAULTS:
        raise KeyError(f"Setting desconocido: {key}")
    env_key = _env_key_for(key)
    if env_key:
        env_val = _env_value_for(env_key, type(DEFAULTS[key]))
        if env_val is not None:
            return env_val
    persisted = load()
    if key in persisted:
        return persisted[key]
    return DEFAULTS[key]


def set_value(key: str, value: Any) -> None:
    """Persiste un setting individual en settings.json."""
    if key not in DEFAULTS:
        raise KeyError(f"Setting desconocido: {key}")
    values = load()
    values[key] = value
    save(values)


def _env_key_for(setting_key: str) -> str | None:
    return {
        "gemini_model": "GEMINI_MODEL",
        "mercadona_warehouse": "MERCADONA_WAREHOUSE",
        "mercadona_max_eur": "MERCADONA_MAX_EUR",
    }.get(setting_key)


def _env_value_for(env_key: str, target_type: type) -> Any:
    import os
    raw = os.getenv(env_key)
    if raw is None:
        return None
    try:
        if target_type is bool:
            return raw.lower() in ("1", "true", "yes", "on")
        if target_type is int:
            return int(raw)
        if target_type is float:
            return float(raw)
        return raw
    except (ValueError, TypeError):
        return None
