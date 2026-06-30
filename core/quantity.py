"""
Parseo de cantidades tipo "200g", "1.5 kg", "3 unidades", "2 latas" → float.
"""
import re

_UNIT_TO_BASE = {
    "g": 1.0,
    "gr": 1.0,
    "kg": 1000.0,
    "ml": 1.0,
    "l": 1000.0,
    "ud": 1.0,
    "uds": 1.0,
    "u": 1.0,
    "unidad": 1.0,
    "unidades": 1.0,
    "lata": 1.0,
    "latas": 1.0,
    "paquete": 1.0,
    "paquetes": 1.0,
    "": 1.0,
}

_NUM_RE = re.compile(r"(\d+(?:[.,]\d+)?)")


def parse_quantity(raw: str) -> float:
    """
    Devuelve la cantidad en la unidad base (g para peso, ml para volumen, ud para piezas).
    Si no se puede parsear, devuelve 1.0.
    """
    if not raw:
        return 1.0
    s = str(raw).lower().strip().replace(",", ".")
    m = _NUM_RE.search(s)
    if not m:
        return 1.0
    try:
        n = float(m.group(1))
    except ValueError:
        return 1.0

    unit = _NUM_RE.sub("", s).strip()
    unit = re.sub(r"\s+", " ", unit)
    factor = _UNIT_TO_BASE.get(unit, 1.0)
    return max(0.0, round(n * factor, 4))
