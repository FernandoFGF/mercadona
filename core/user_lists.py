"""
Storage de listas personales del usuario: pantry (lo que ya tengo en casa)
y avoid (lo que no quiero comprar). Persistencia en JSON.

API:
    PantryStore.contains(term) -> bool          # fuzzy match, threshold 85
    PantryStore.add(term), remove(term), list()
    AvoidStore.contains(term) -> bool
    AvoidStore.add(term), remove(term), list()
"""
import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable

import config

try:
    from rapidfuzz import fuzz  # type: ignore
    _HAS_RAPIDFUZZ = True
except Exception:
    _HAS_RAPIDFUZZ = False


_PANTRY_PATH = config.DATA_DIR / "pantry.json"
_AVOID_PATH = config.DATA_DIR / "avoid.json"

_FUZZY_THRESHOLD = 85


def _pantry_path() -> Path:
    return config.DATA_DIR / "pantry.json"


def _avoid_path() -> Path:
    return config.DATA_DIR / "avoid.json"


def _normalize(s: str) -> str:
    return s.lower().strip()


def _score(a: str, b: str) -> float:
    a, b = _normalize(a), _normalize(b)
    if _HAS_RAPIDFUZZ:
        return max(fuzz.token_set_ratio(a, b), fuzz.WRatio(a, b))
    return SequenceMatcher(None, a, b).ratio() * 100


class _ListStore:
    path: Path
    event_name: str = "list_changed"

    def __init__(self):
        self.path = self._resolve_path()

    def _resolve_path(self) -> Path:
        raise NotImplementedError

    def _load(self) -> list[str]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [str(x) for x in data]
        except (OSError, json.JSONDecodeError):
            pass
        return []

    def _save(self, items: list[str]) -> None:
        try:
            self.path.write_text(
                json.dumps(sorted(set(items)), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    def _emit(self) -> None:
        try:
            from core.event_bus import default_bus
            default_bus.emit(self.event_name, self.__class__.__name__)
        except Exception:
            pass

    def list(self) -> list[str]:
        return self._load()

    def add(self, term: str) -> bool:
        term = _normalize(term)
        if not term:
            return False
        items = self._load()
        if any(_score(term, it) >= 99 for it in items):
            return False
        items.append(term)
        self._save(items)
        self._emit()
        return True

    def remove(self, term: str) -> bool:
        term_n = _normalize(term)
        items = self._load()
        new_items = [it for it in items if _normalize(it) != term_n]
        if len(new_items) == len(items):
            return False
        self._save(new_items)
        self._emit()
        return True

    def contains(self, term: str) -> bool:
        term_n = _normalize(term)
        if not term_n:
            return False
        for it in self._load():
            if _score(term_n, _normalize(it)) >= _FUZZY_THRESHOLD:
                return True
        return False

    def filter_out(self, terms: Iterable[str]) -> list[str]:
        """Devuelve los términos que NO están en la lista."""
        out = []
        for t in terms:
            if not self.contains(t):
                out.append(t)
        return out


class PantryStore(_ListStore):
    event_name = "pantry_changed"

    def _resolve_path(self) -> Path:
        return _pantry_path()


class AvoidStore(_ListStore):
    event_name = "avoid_changed"

    def _resolve_path(self) -> Path:
        return _avoid_path()
