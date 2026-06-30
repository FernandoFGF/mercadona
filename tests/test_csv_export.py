"""Tests del cart engine: CSV export."""
from core.cart_engine import Cart


def _prod(pid, name="prod", price=1.0):
    return {"id": pid, "name": name, "price": price}


def test_to_csv_header_and_rows():
    c = Cart()
    c.add(_prod(7, "arroz", 1.5), quantity=2, origin="receta1")
    c.add(_prod(8, "leche", 1.1), quantity=1, origin="")
    out = c.to_csv()
    lines = [l for l in out.replace("\r\n", "\n").strip().split("\n") if l]
    assert lines[0] == "id,producto,cantidad,precio_unit,subtotal,origen"
    assert len(lines) == 3
    assert "arroz" in lines[1] and "2" in lines[1] and "receta1" in lines[1]
    assert "leche" in lines[2]


def test_to_csv_empty():
    c = Cart()
    out = c.to_csv()
    assert out.strip() == "id,producto,cantidad,precio_unit,subtotal,origen"


def test_to_csv_special_chars_quoted():
    c = Cart()
    c.add(_prod(1, 'tomate "ecológico"', 2.0), quantity=1, origin='origen, con coma')
    out = c.to_csv()
    # csv escapa comillas duplicándolas
    assert 'tomate ""ecológico""' in out
    assert 'origen, con coma' in out
