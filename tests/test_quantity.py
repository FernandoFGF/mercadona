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
