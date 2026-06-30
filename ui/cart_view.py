"""
Vista: carrito de la compra. Lista, total, exportar a basket-file, vaciar.
"""
import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.cart_engine import Cart
from core.user_lists import PantryStore


class CartView(ctk.CTkFrame):
    def __init__(self, master, cart: Cart):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.cart = cart
        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 5))

        ctk.CTkLabel(
            header, text="🛒 Cart", font=ctk.CTkFont(size=22, weight="bold")
        ).pack(side="left")

        self.total_lbl = ctk.CTkLabel(header, text="Total: 0.00 €", font=ctk.CTkFont(size=18, weight="bold"))
        self.total_lbl.pack(side="right")

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=5)

        ctk.CTkButton(actions, text="Exportar basket.txt", command=self.export_basket, width=160).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkButton(actions, text="Exportar CSV", command=self.export_csv, width=120).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkButton(
            actions, text="Vaciar carrito", command=self.clear_cart, fg_color="#a33", hover_color="#822", width=120
        ).pack(side="left")

        ctk.CTkLabel(
            self,
            text="El basket.txt se puede usar con:  mercadona total -f basket.txt   o   mercadona cart set-many -f basket.txt",
            text_color="gray",
        ).pack(anchor="w", padx=20, pady=(0, 8))

        self.status = ctk.CTkLabel(self, text="", text_color="gray")
        self.status.pack(anchor="w", padx=20, pady=(0, 4))

        self.list = ctk.CTkScrollableFrame(self, label_text="Productos")
        self.list.pack(fill="both", expand=True, padx=20, pady=10)
        self.refresh()

    def refresh(self):
        for w in self.list.winfo_children():
            w.destroy()
        if not self.cart.items:
            ctk.CTkLabel(self.list, text="(carrito vacío)").pack(padx=10, pady=10)
        for it in self.cart.items:
            row = ctk.CTkFrame(self.list)
            row.pack(fill="x", padx=8, pady=4)
            ctk.CTkLabel(row, text=f"#{it.product_id}", width=60, anchor="w").pack(side="left", padx=8)
            ctk.CTkLabel(row, text=it.name, anchor="w", wraplength=240, justify="left").pack(
                side="left", padx=8, fill="x", expand=True
            )
            ctk.CTkLabel(row, text=f"{it.unit_price:.2f} €", width=70, anchor="e").pack(side="right", padx=2)
            ctk.CTkLabel(row, text=f"{it.subtotal:.2f} €", width=70, anchor="e").pack(side="right", padx=2)

            ctk.CTkButton(
                row, text="🏺", width=32, fg_color="#363", hover_color="#242",
                command=lambda n=it.name: self._add_to_pantry(n),
            ).pack(side="right", padx=2)
            ctk.CTkButton(
                row, text="🗑", width=32, fg_color="#a33", hover_color="#822",
                command=lambda pid=it.product_id: self.remove(pid),
            ).pack(side="right", padx=2)

            ctk.CTkButton(
                row, text="−", width=32,
                command=lambda pid=it.product_id, q=it.quantity: self._bump(pid, q, -1),
            ).pack(side="right", padx=2)
            ctk.CTkButton(
                row, text="+", width=32,
                command=lambda pid=it.product_id, q=it.quantity: self._bump(pid, q, +1),
            ).pack(side="right", padx=2)

            qty_var = ctk.StringVar(value=f"{it.quantity:g}")
            entry = ctk.CTkEntry(row, textvariable=qty_var, width=60, justify="right")
            entry.pack(side="right", padx=4)
            entry.bind(
                "<Return>",
                lambda _e, pid=it.product_id, var=qty_var: self._commit_qty(pid, var),
            )
            entry.bind(
                "<FocusOut>",
                lambda _e, pid=it.product_id, var=qty_var: self._commit_qty(pid, var),
            )
        self.total_lbl.configure(text=f"Total: {self.cart.total():.2f} €")

    def remove(self, pid):
        self.cart.remove(pid)
        self.refresh()

    def _add_to_pantry(self, name: str):
        """Marca este producto como 'ya lo tengo en casa' para futuras recetas."""
        if not name:
            return
        store = PantryStore()
        if store.add(name):
            self.status.configure(text=f"Añadido a pantry: {name}")

    def _bump(self, pid, current_qty: float, delta: int):
        new_qty = max(0.0, round(float(current_qty) + delta, 4))
        if new_qty <= 0:
            self.cart.remove(pid)
        else:
            self.cart.update_qty(pid, new_qty)
        self.refresh()

    def _commit_qty(self, pid, qty_var: ctk.StringVar):
        raw = qty_var.get().strip().replace(",", ".")
        try:
            new_qty = float(raw)
        except ValueError:
            self.refresh()
            return
        if new_qty <= 0:
            self.cart.remove(pid)
        else:
            self.cart.update_qty(pid, new_qty)
        self.refresh()

    def clear_cart(self):
        if messagebox.askyesno("Vaciar carrito", "¿Vaciar todos los productos?"):
            self.cart.clear()
            self.refresh()

    def export_basket(self):
        if not self.cart.items:
            messagebox.showinfo("Vacío", "No hay productos en el carrito.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Basket", "*.txt")], initialfile="basket.txt"
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.cart.to_basket())
        messagebox.showinfo("Exportado", f"Basket guardado en:\n{path}")

    def export_csv(self):
        if not self.cart.items:
            messagebox.showinfo("Vacío", "No hay productos en el carrito.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")], initialfile="basket.csv"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(self.cart.to_csv())
        except OSError as e:
            messagebox.showerror("Error", f"No se pudo escribir el archivo:\n{e}")
            return
        messagebox.showinfo("Exportado", f"CSV guardado en:\n{path}")
