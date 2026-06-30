"""
Vista genérica para listas del usuario (pantry / avoid).
"""
import customtkinter as ctk
from tkinter import messagebox

from core.event_bus import default_bus
from core.user_lists import _ListStore


class SimpleListView(ctk.CTkFrame):
    def __init__(self, master, store: _ListStore, title: str, hint: str, empty_msg: str):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.store = store
        self._build(title, hint, empty_msg)
        self.refresh()
        # Suscribirse al evento de cambio para refrescar cuando otra vista añade algo
        default_bus.on(store.event_name, self._on_external_change)

    def _on_external_change(self, _class_name: str = "") -> None:
        """Callback del bus cuando se modifica la lista desde otra vista."""
        try:
            self.refresh()
        except Exception:
            pass

    def _build(self, title: str, hint: str, empty_msg: str):
        self.empty_msg = empty_msg
        ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=22, weight="bold")).pack(
            anchor="w", padx=20, pady=(20, 5)
        )
        ctk.CTkLabel(self, text=hint, text_color="gray").pack(anchor="w", padx=20)

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=20, pady=10)
        self.entry = ctk.CTkEntry(bar, placeholder_text="Añadir término y Enter…")
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry.bind("<Return>", lambda _e: self._add())

        ctk.CTkButton(bar, text="Añadir", command=self._add, width=100).pack(side="left")

        self.list = ctk.CTkScrollableFrame(self, label_text="Items")
        self.list.pack(fill="both", expand=True, padx=20, pady=10)

    def refresh(self):
        for w in self.list.winfo_children():
            w.destroy()
        items = self.store.list()
        if not items:
            ctk.CTkLabel(self.list, text=self.empty_msg).pack(padx=10, pady=10)
            return
        for term in items:
            row = ctk.CTkFrame(self.list)
            row.pack(fill="x", padx=8, pady=4)
            ctk.CTkLabel(row, text=term, anchor="w").pack(
                side="left", padx=8, fill="x", expand=True
            )
            ctk.CTkButton(
                row, text="🗑️", width=40, fg_color="#a33", hover_color="#822",
                command=lambda t=term: self._remove(t),
            ).pack(side="right", padx=4)

    def _add(self):
        term = self.entry.get().strip()
        if not term:
            return
        if not self.store.add(term):
            messagebox.showinfo("Duplicado", f"'{term}' ya está en la lista.")
            return
        self.entry.delete(0, "end")
        self.refresh()

    def _remove(self, term: str):
        if messagebox.askyesno("Eliminar", f"¿Quitar '{term}'?"):
            self.store.remove(term)
            self.refresh()
