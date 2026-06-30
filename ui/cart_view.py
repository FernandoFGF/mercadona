"""
Vista: carrito de la compra. Lista, total, exportar a basket-file, vaciar.
"""
import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.cart_engine import Cart


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
        ctk.CTkButton(
            actions, text="Vaciar carrito", command=self.clear_cart, fg_color="#a33", hover_color="#822", width=120
        ).pack(side="left")

        ctk.CTkLabel(
            self,
            text="El basket.txt se puede usar con:  mercadona total -f basket.txt   o   mercadona cart set-many -f basket.txt",
            text_color="gray",
        ).pack(anchor="w", padx=20, pady=(0, 8))

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
            ctk.CTkLabel(row, text=it.name, anchor="w", wraplength=400, justify="left").pack(
                side="left", padx=8, fill="x", expand=True
            )
            ctk.CTkLabel(row, text=f"{it.unit_price:.2f} €", width=80, anchor="e").pack(side="right", padx=4)
            ctk.CTkLabel(row, text=f"x{it.quantity:g}", width=60, anchor="e").pack(side="right", padx=4)
            ctk.CTkLabel(row, text=f"{it.subtotal:.2f} €", width=80, anchor="e").pack(side="right", padx=4)
            ctk.CTkButton(row, text="✕", width=30, command=lambda pid=it.product_id: self.remove(pid)).pack(
                side="right", padx=4
            )
        self.total_lbl.configure(text=f"Total: {self.cart.total():.2f} €")

    def remove(self, pid):
        self.cart.remove(pid)
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
