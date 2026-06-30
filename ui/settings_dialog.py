"""
Diálogo modal de settings: temperatura, modelo Gemini, warehouse Mercadona,
tope de gasto, apariencia. Lee/escribe via core.settings_store.
"""
import customtkinter as ctk
from tkinter import messagebox

from core import settings_store


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, master, on_appearance_change=None):
        super().__init__(master)
        self.title("Ajustes")
        self.geometry("480x420")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.on_appearance_change = on_appearance_change

        ctk.CTkLabel(self, text="Ajustes", font=ctk.CTkFont(size=20, weight="bold")).pack(
            anchor="w", padx=20, pady=(20, 4)
        )
        ctk.CTkLabel(
            self, text="Los valores se persisten en data/settings.json. Las variables de entorno tienen prioridad.",
            text_color="gray", wraplength=440,
        ).pack(anchor="w", padx=20)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=20)

        # Modelo Gemini
        ctk.CTkLabel(body, text="Modelo Gemini:").grid(row=0, column=0, sticky="w", pady=6)
        self.model_var = ctk.StringVar(value=str(settings_store.get("gemini_model")))
        ctk.CTkEntry(body, textvariable=self.model_var, width=280).grid(row=0, column=1, sticky="ew", padx=10)

        # Temperatura
        ctk.CTkLabel(body, text="Temperatura:").grid(row=1, column=0, sticky="w", pady=6)
        self.temp_var = ctk.StringVar(value=str(settings_store.get("gemini_temperature")))
        ctk.CTkEntry(body, textvariable=self.temp_var, width=120).grid(row=1, column=1, sticky="w", padx=10)

        # Warehouse
        ctk.CTkLabel(body, text="Warehouse Mercadona:").grid(row=2, column=0, sticky="w", pady=6)
        self.wh_var = ctk.StringVar(value=str(settings_store.get("mercadona_warehouse")))
        ctk.CTkEntry(body, textvariable=self.wh_var, width=120).grid(row=2, column=1, sticky="w", padx=10)

        # Tope EUR
        ctk.CTkLabel(body, text="Tope gasto (€, 0=sin tope):").grid(row=3, column=0, sticky="w", pady=6)
        self.max_var = ctk.StringVar(value=str(settings_store.get("mercadona_max_eur")))
        ctk.CTkEntry(body, textvariable=self.max_var, width=120).grid(row=3, column=1, sticky="w", padx=10)

        # Apariencia
        ctk.CTkLabel(body, text="Apariencia:").grid(row=4, column=0, sticky="w", pady=6)
        self.appearance_var = ctk.StringVar(value=str(settings_store.get("appearance_mode")))
        ctk.CTkSegmentedButton(
            body, values=["dark", "light"], variable=self.appearance_var, width=200,
        ).grid(row=4, column=1, sticky="w", padx=10)

        # Matching semántico
        ctk.CTkLabel(body, text="Matching semántico:").grid(row=5, column=0, sticky="w", pady=6)
        self.embeddings_var = ctk.BooleanVar(value=bool(settings_store.get("usar_embeddings")))
        ctk.CTkSwitch(
            body, text="", variable=self.embeddings_var, width=50,
        ).grid(row=5, column=1, sticky="w", padx=10)
        ctk.CTkLabel(
            body,
            text="Desactívalo si ves errores 429\n(cuota de Gemini agotada)",
            text_color="gray",
        ).grid(row=6, column=1, sticky="w", padx=10)

        body.grid_columnconfigure(1, weight=1)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkButton(btns, text="Cancelar", command=self.destroy, width=100, fg_color="gray").pack(side="right", padx=6)
        ctk.CTkButton(btns, text="Guardar", command=self._save, width=100).pack(side="right")

    def _save(self):
        try:
            temp = float(self.temp_var.get().strip())
            max_eur = float(self.max_var.get().strip() or "0")
        except ValueError:
            messagebox.showerror("Error", "Temperatura y tope deben ser números.")
            return
        if not (0.0 <= temp <= 2.0):
            messagebox.showerror("Error", "La temperatura debe estar entre 0 y 2.")
            return
        if max_eur < 0:
            messagebox.showerror("Error", "El tope no puede ser negativo.")
            return

        new_appearance = self.appearance_var.get()
        old_appearance = str(settings_store.get("appearance_mode"))

        settings_store.set_value("gemini_model", self.model_var.get().strip())
        settings_store.set_value("gemini_temperature", temp)
        settings_store.set_value("mercadona_warehouse", self.wh_var.get().strip() or "mad1")
        settings_store.set_value("mercadona_max_eur", max_eur)
        settings_store.set_value("appearance_mode", new_appearance)
        settings_store.set_value("usar_embeddings", bool(self.embeddings_var.get()))
        # Si reactivamos embeddings, reseteamos el circuit breaker.
        if self.embeddings_var.get():
            try:
                from core import semantic_matcher
                semantic_matcher.reset_circuit()
            except Exception:
                pass

        if new_appearance != old_appearance and self.on_appearance_change:
            self.on_appearance_change(new_appearance)

        self.destroy()
