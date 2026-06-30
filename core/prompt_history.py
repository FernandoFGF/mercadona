"""
Historial de prompts del usuario. Persistencia en JSON.
Mantiene las últimas N entradas (la más reciente primero).
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import config


_MAX_ENTRIES = 10


def _path() -> Path:
    return config.DATA_DIR / "prompt_history.json"


def load() -> list[dict[str, Any]]:
    p = _path()
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return []


def save(entries: list[dict[str, Any]]) -> None:
    try:
        _path().write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def add(prompt: str) -> list[dict[str, Any]]:
    """
    Añade un prompt al historial. Si ya existe (case-insensitive, trimmed),
    lo mueve al principio. Devuelve el historial actualizado.
    """
    prompt = prompt.strip()
    if not prompt:
        return load()
    entries = [e for e in load() if e.get("text", "").strip().lower() != prompt.lower()]
    entries.insert(0, {"text": prompt, "ts": datetime.now().isoformat(timespec="seconds")})
    entries = entries[:_MAX_ENTRIES]
    save(entries)
    return entries


def clear() -> None:
    save([])
