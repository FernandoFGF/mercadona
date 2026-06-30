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


def is_weight_or_volume(unit_str: str) -> bool:
    """True si la unidad es de peso (g/kg/gr) o volumen (ml/l)."""
    if not unit_str:
        return False
    u = unit_str.lower().strip()
    return any(t in u for t in ("g", "kg", "ml", "l", "litro", "gramo"))


def extract_unit(raw: str) -> str:
    """Devuelve la unidad detectada en la cadena (ej. 'kg', 'ml', 'unidades', '')."""
    if not raw:
        return ""
    s = str(raw).lower().strip()
    m = _NUM_RE.search(s)
    if not m:
        return ""
    unit = _NUM_RE.sub("", s).strip()
    return re.sub(r"\s+", " ", unit)


def normalize_for_cart(quantity: float, unit_str: str, product_name: str = "") -> float:
    """
    Ajusta una cantidad parseada para que tenga sentido en el carrito.

    El parser devuelve gramos/ml. Mercadona vende por kg/litro normalmente, así
    que si la cantidad > 5 y la unidad es g/ml, dividimos entre 1000 para pasarla
    a kg/litro. Para unidades, devolvemos la cantidad tal cual (hasta el tope
    que aplica Cart.add).
    """
    if quantity <= 0:
        return 0.0
    if is_weight_or_volume(unit_str) and quantity > 5:
        # 5g/5ml es ya muy poco. Si Gemini dijo "200g" o más, lo pasamos a kg/l.
        return round(quantity / 1000.0, 4)
    return quantity
