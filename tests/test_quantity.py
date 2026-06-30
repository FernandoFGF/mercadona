"""Tests del parser de cantidades."""
import pytest

from core.quantity import parse_quantity


@pytest.mark.parametrize("raw,expected", [
    ("200g", 200.0),
    ("200 g", 200.0),
    ("1.5 kg", 1500.0),
    ("1,5kg", 1500.0),
    ("500gr", 500.0),
    ("400 ml", 400.0),
    ("1l", 1000.0),
    ("1 l", 1000.0),
    ("3 unidades", 3.0),
    ("1 unidad", 1.0),
    ("2 latas", 2.0),
    ("1 paquete", 1.0),
    ("", 1.0),
    ("abc", 1.0),
    (None, 1.0),
])
def test_parse_quantity(raw, expected):
    assert parse_quantity(raw) == expected


def test_parse_quantity_zero():
    assert parse_quantity("0g") == 0.0


def test_cart_quantity_clamped_to_ceiling():
    """Red de seguridad: cart_engine.add() no deja pasar cantidades absurdas."""
    from core.cart_engine import Cart
    c = Cart()
    c.add({"id": 1, "name": "quinoa", "price": 7.0}, quantity=99999.0, origin="x")
    assert c.items[0].quantity == 1000.0


def test_cart_quantity_clamped_on_consolidation():
    """Aunque se sume en varias llamadas, no se supera el tope."""
    from core.cart_engine import Cart
    c = Cart()
    for _ in range(20):
        c.add({"id": 1, "name": "quinoa", "price": 7.0}, quantity=500.0, origin="x")
    assert c.items[0].quantity == 1000.0
    assert c.total() == 7000.0  # tope, no 70000
