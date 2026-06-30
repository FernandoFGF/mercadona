"""
Carrito de la compra: agrupa productos por id, calcula totales, permite
exportar a basket-file (formato `mercadona total` / `mercadona cart set-many`).
"""
from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class CartItem:
    product_id: int | str
    name: str
    unit_price: float
    quantity: float = 1.0
    ingredient_origin: str = ""

    @property
    def subtotal(self) -> float:
        return round(self.unit_price * self.quantity, 2)


@dataclass
class Cart:
    items: list[CartItem] = field(default_factory=list)

    def add(self, product: dict, quantity: float = 1.0, origin: str = "") -> None:
        pid = product.get("id")
        if pid is None:
            return
        qty = max(0.0, float(quantity))
        for it in self.items:
            if it.product_id == pid:
                it.quantity = round(it.quantity + qty, 4)
                return
        self.items.append(
            CartItem(
                product_id=pid,
                name=product.get("name", "?"),
                unit_price=float(product.get("price", 0.0) or 0.0),
                quantity=round(qty, 4),
                ingredient_origin=origin,
            )
        )

    def update_qty(self, product_id, quantity: float) -> None:
        qty = max(0.0, float(quantity))
        for it in self.items:
            if it.product_id == product_id:
                if qty <= 0:
                    self.remove(product_id)
                    return
                it.quantity = round(qty, 4)
                return

    def remove(self, product_id) -> None:
        self.items = [it for it in self.items if it.product_id != product_id]

    def clear(self) -> None:
        self.items.clear()

    def total(self) -> float:
        return round(sum(it.subtotal for it in self.items), 2)

    def to_basket(self) -> str:
        """Formato texto para `mercadona total -f -` y `mercadona cart set-many -f -`."""
        lines = ["# AI Grocery Planner basket"]
        for it in self.items:
            qty = f"{it.quantity:g}"
            comment = f"  # {it.ingredient_origin}" if it.ingredient_origin else ""
            lines.append(f"{it.product_id} {qty}{comment}")
        return "\n".join(lines)

    def merge(self, items: Iterable[CartItem]) -> None:
        for it in items:
            self.add(
                {"id": it.product_id, "name": it.name, "price": it.unit_price},
                quantity=it.quantity,
                origin=it.ingredient_origin,
            )

    def to_csv(self) -> str:
        """Exporta el carrito a CSV con cabecera fija."""
        import csv
        import io
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "producto", "cantidad", "precio_unit", "subtotal", "origen"])
        for it in self.items:
            writer.writerow([
                it.product_id,
                it.name,
                f"{it.quantity:g}",
                f"{it.unit_price:.2f}",
                f"{it.subtotal:.2f}",
                it.ingredient_origin,
            ])
        return buf.getvalue()
