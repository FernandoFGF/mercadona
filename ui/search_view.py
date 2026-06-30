"""
Vista: búsqueda manual de productos en Mercadona + añadir al carrito.
"""
import json
import threading
from pathlib import Path

import customtkinter as ctk
from tkinter import messagebox

from adapters import mercadona_cli
from core.cart_engine import Cart
from core.user_lists import PantryStore, AvoidStore
import config


_DEFAULT_MATCHES_PATH = config.DATA_DIR / "default_matches.json"


def _load_default_matches() -> dict[str, int | str]:
    if not _DEFAULT_MATCHES_PATH.exists():
        return {}
    try:
        return json.loads(_DEFAULT_MATCHES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_default_matches(matches: dict[str, int | str]) -> None:
    try:
        _DEFAULT_MATCHES_PATH.write_text(
            json.dumps(matches, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


class SearchView(ctk.CTkFrame):
    def __init__(self, master, cart: Cart, on_cart_updated):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.cart = cart
        self.on_cart_updated = on_cart_updated
        self._hits: list[dict] = []
        self._default_matches = _load_default_matches()
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
        current_query = self.query.get().strip()
        for h in self._hits:
            name = h.get("display_name") or h.get("name") or h.get("product_name") or "?"
            pid = h.get("id")
            pi = h.get("price_instructions", {}) if isinstance(h.get("price_instructions"), dict) else {}
            price = pi.get("unit_price") or h.get("unit_price") or h.get("price") or 0
            ref = h.get("reference_price") or ""
            row = ctk.CTkFrame(self.results)
            row.pack(fill="x", padx=8, pady=4)
            ctk.CTkLabel(row, text=name, anchor="w", wraplength=300, justify="left").pack(
                side="left", padx=8, fill="x", expand=True
            )
            ctk.CTkLabel(row, text=f"{float(price):.2f} €", width=70, anchor="e").pack(side="right", padx=2)
            if ref:
                ctk.CTkLabel(row, text=str(ref), width=90, anchor="e", text_color="gray").pack(
                    side="right", padx=2
                )
            ctk.CTkButton(
                row,
                text="+ Carrito",
                width=80,
                command=lambda p=h: self._add(p),
            ).pack(side="right", padx=2)
            ctk.CTkButton(
                row,
                text="★ Match",
                width=70,
                fg_color="#356",
                hover_color="#234",
                command=lambda p=h, q=current_query: self._save_default(q, p),
            ).pack(side="right", padx=2)
            ctk.CTkButton(
                row,
                text="🏺 +",
                width=36,
                fg_color="#363",
                hover_color="#242",
                command=lambda p=h, q=current_query: self._add_to_list("pantry", q, p),
            ).pack(side="right", padx=2)
            ctk.CTkButton(
                row,
                text="🚫 +",
                width=36,
                fg_color="#a33",
                hover_color="#822",
                command=lambda p=h, q=current_query: self._add_to_list("avoid", q, p),
            ).pack(side="right", padx=2)

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

    def _save_default(self, term: str, product: dict):
        if not term:
            return
        pid = product.get("id")
        if pid is None:
            return
        self._default_matches[term.lower().strip()] = pid
        _save_default_matches(self._default_matches)
        name = product.get("display_name") or product.get("name") or str(pid)
        self.status.configure(text=f"Guardado como match por defecto para '{term}': {name}")

    def _add_to_list(self, list_name: str, term: str, product: dict):
        """Añade el término (o nombre del producto si no hay query) a pantry o avoid."""
        store = PantryStore() if list_name == "pantry" else AvoidStore()
        label = "pantry" if list_name == "pantry" else "avoid"
        # Priorizar el nombre del producto; si no, el término buscado
        name = (
            product.get("display_name") or product.get("name") or product.get("product_name")
            or term
        ).strip()
        if not name:
            return
        if not store.add(name):
            messagebox.showinfo("Ya está", f"'{name}' ya está en {label}.")
            return
        self.status.configure(text=f"Añadido a {label}: {name}")
