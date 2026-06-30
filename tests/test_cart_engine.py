"""Tests del cart engine: sumas, dedupe por product_id, export basket, update_qty."""
from core.cart_engine import Cart


def _prod(pid, name="prod", price=1.0):
    return {"id": pid, "name": name, "price": price}


def test_add_single():
    c = Cart()
    c.add(_prod(1, "arroz", 1.5))
    assert len(c.items) == 1
    assert c.items[0].quantity == 1.0
    assert c.total() == 1.5


def test_add_dedupes_by_product_id():
    c = Cart()
    c.add(_prod(1, "arroz", 1.5), quantity=2)
    c.add(_prod(1, "arroz", 1.5), quantity=3)
    assert len(c.items) == 1
    assert c.items[0].quantity == 5
    assert c.total() == 7.5


def test_add_separate_ids():
    c = Cart()
    c.add(_prod(1, "arroz", 1.0), quantity=2)
    c.add(_prod(2, "leche", 1.2), quantity=1)
    assert len(c.items) == 2
    assert c.total() == round(2 * 1.0 + 1 * 1.2, 2)


def test_add_none_id_is_ignored():
    c = Cart()
    c.add({"id": None, "name": "x", "price": 1.0})
    assert c.items == []


def test_remove_by_id():
    c = Cart()
    c.add(_prod(1))
    c.add(_prod(2))
    c.remove(1)
    assert [it.product_id for it in c.items] == [2]


def test_clear():
    c = Cart()
    c.add(_prod(1))
    c.add(_prod(2))
    c.clear()
    assert c.items == []


def test_update_qty():
    c = Cart()
    c.add(_prod(1, price=2.0), quantity=1)
    c.update_qty(1, 4)
    assert c.items[0].quantity == 4
    assert c.total() == 8.0


def test_update_qty_to_zero_removes():
    c = Cart()
    c.add(_prod(1), quantity=2)
    c.update_qty(1, 0)
    assert c.items == []


def test_update_qty_unknown_id_is_noop():
    c = Cart()
    c.add(_prod(1), quantity=1)
    c.update_qty(999, 5)
    assert len(c.items) == 1
    assert c.items[0].quantity == 1


def test_to_basket_format():
    c = Cart()
    c.add(_prod(7, "arroz", 1.5), quantity=2, origin="receta1")
    c.add(_prod(8, "leche", 1.1), quantity=1, origin="")
    out = c.to_basket()
    assert "# AI Grocery Planner basket" in out
    assert "7 2  # receta1" in out
    assert "8 1" in out


def test_total_rounds():
    c = Cart()
    c.add(_prod(1, price=0.333), quantity=3)
    assert c.total() == round(0.333 * 3, 2)


def test_merge_combines_items():
    c = Cart()
    c.add(_prod(1, price=1.0), quantity=1)
    from core.cart_engine import CartItem
    other = [CartItem(product_id=1, name="arroz", unit_price=1.0, quantity=2)]
    c.merge(other)
    assert c.items[0].quantity == 3
