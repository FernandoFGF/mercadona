"""
Vista: búsqueda manual de productos en Mercadona + añadir al carrito.
"""
import threading
import customtkinter as ctk

from adapters import mercadona_cli
from core.cart_engine import Cart


class SearchView(ctk.CTkFrame):
    def __init__(self, master, cart: Cart, on_cart_updated):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.cart = cart
        self.on_cart_updated = on_cart_updated
        self._hits: list[dict] = []
        self._build()

    def _build(self):
        ctk.CTkLabel(
            self, text="🔍 Product Search", font=ctk.CTkFont(size=22, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 5))

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=20, pady=10)

        self.query = ctk.CTkEntry(bar, placeholder_text="Ej: arroz redondo, pechuga de pollo…")
        self.query.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.query.bind("<Return>", lambda _e: self.do_search())

        self.fresh_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(bar, text="Solo frescos", variable=self.fresh_var).pack(side="left", padx=8)

        ctk.CTkButton(bar, text="Buscar", command=self.do_search, width=100).pack(side="left")

        self.status = ctk.CTkLabel(self, text="", text_color="gray")
        self.status.pack(anchor="w", padx=20)

        self.results = ctk.CTkScrollableFrame(self, label_text="Resultados")
        self.results.pack(fill="both", expand=True, padx=20, pady=10)

    def do_search(self):
        q = self.query.get().strip()
        if not q:
            return
        self.status.configure(text="Buscando…")
        threading.Thread(target=self._worker, args=(q, self.fresh_var.get()), daemon=True).start()

    def _worker(self, q: str, fresh: bool):
        try:
            hits = mercadona_cli.search(q, limit=10, fresh=fresh)
        except Exception as e:
            err = e
            self.after(0, lambda: self.status.configure(text=f"Error: {err}", text_color="red"))
            return
        self._hits = hits
        self.after(0, self._render)

    def _render(self):
        for w in self.results.winfo_children():
            w.destroy()
        self.status.configure(text=f"{len(self._hits)} resultados")
        for h in self._hits:
            name = h.get("display_name") or h.get("name") or h.get("product_name") or "?"
            pid = h.get("id")
            pi = h.get("price_instructions", {}) if isinstance(h.get("price_instructions"), dict) else {}
            price = pi.get("unit_price") or h.get("unit_price") or h.get("price") or 0
            ref = h.get("reference_price") or ""
            row = ctk.CTkFrame(self.results)
            row.pack(fill="x", padx=8, pady=4)
            ctk.CTkLabel(row, text=name, anchor="w", wraplength=500, justify="left").pack(
                side="left", padx=8, fill="x", expand=True
            )
            ctk.CTkLabel(row, text=f"{float(price):.2f} €", width=80, anchor="e").pack(side="right", padx=4)
            if ref:
                ctk.CTkLabel(row, text=str(ref), width=110, anchor="e", text_color="gray").pack(
                    side="right", padx=4
                )
            ctk.CTkButton(
                row,
                text="+ Añadir",
                width=90,
                command=lambda p=h: self._add(p),
            ).pack(side="right", padx=4)

    def _add(self, product: dict):
        pi = product.get("price_instructions", {}) if isinstance(product.get("price_instructions"), dict) else {}
        normalized = {
            "id": product.get("id"),
            "name": product.get("display_name") or product.get("name") or "producto",
            "price": pi.get("unit_price") or product.get("unit_price") or product.get("price") or 0.0,
        }
        self.cart.add(normalized, quantity=1.0, origin="búsqueda manual")
        self.on_cart_updated()
        self.status.configure(text=f"Añadido: {normalized['name']}")
