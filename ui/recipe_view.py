"""
Vista: generación de recetas con Gemini y volcado al carrito.
"""
import queue
import threading
from tkinter import filedialog, messagebox
import customtkinter as ctk

from core import recipe_engine, product_matcher
from core.cart_engine import Cart, CartItem
from core.logging_setup import get_logger
from core.prompt_history import add as history_add, load as history_load, clear as history_clear
from core.quantity import parse_quantity, normalize_for_cart, extract_unit
from core.recipe_engine import DIETARY_RESTRICTIONS
from core.recipe_exporter import render_recipes_markdown
from core.user_lists import PantryStore, AvoidStore


class RecipeView(ctk.CTkFrame):
    def __init__(self, master, cart: Cart, on_cart_updated):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.cart = cart
        self.on_cart_updated = on_cart_updated
        self._last_plan: dict | None = None
        self._last_prompt: str = ""
        self._progress_q: queue.Queue = queue.Queue()
        self._build()

    def _build(self):
        ctk.CTkLabel(
            self, text="🥗 Recipe Generator", font=ctk.CTkFont(size=22, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 5))

        ctk.CTkLabel(
            self,
            text='Pide lo que quieras: "algo sano y bajo en colesterol", "menú de 5 días bajo en calorías"...',
            text_color="gray",
        ).pack(anchor="w", padx=20)

        # M-04: Historial de prompts (dropdown)
        hist_row = ctk.CTkFrame(self, fg_color="transparent")
        hist_row.pack(fill="x", padx=20, pady=(10, 0))
        ctk.CTkLabel(hist_row, text="Historial:").pack(side="left", padx=(0, 5))
        self.history_var = ctk.StringVar(value="(vacío)")
        self.history_menu = ctk.CTkOptionMenu(
            hist_row, variable=self.history_var, values=["(vacío)"], width=400, command=self._on_history_pick
        )
        self.history_menu.pack(side="left", padx=(0, 8))
        ctk.CTkButton(hist_row, text="Limpiar", width=70, command=self._on_history_clear).pack(side="left")
        self._refresh_history_menu()

        opts = ctk.CTkFrame(self, fg_color="transparent")
        opts.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(opts, text="Días:").pack(side="left", padx=(0, 5))
        self.days_var = ctk.IntVar(value=1)
        ctk.CTkOptionMenu(opts, values=["1", "2", "3", "5", "7"], variable=self.days_var, width=70).pack(
            side="left", padx=(0, 15)
        )

        ctk.CTkLabel(opts, text="Personas:").pack(side="left", padx=(0, 5))
        self.personas_var = ctk.IntVar(value=2)
        ctk.CTkOptionMenu(
            opts, values=["1", "2", "3", "4", "5", "6"],
            variable=self.personas_var, width=70,
        ).pack(side="left", padx=(0, 15))

        ctk.CTkLabel(opts, text="Dificultad:").pack(side="left", padx=(0, 5))
        self.difficulty_var = ctk.StringVar(value="cualquiera")
        ctk.CTkOptionMenu(
            opts,
            values=["cualquiera", "fácil", "media", "elaborada"],
            variable=self.difficulty_var, width=120,
        ).pack(side="left", padx=(0, 15))

        ctk.CTkLabel(opts, text="Solo frescos:").pack(side="left", padx=(0, 5))
        self.fresh_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(opts, text="", variable=self.fresh_var).pack(side="left")

        self.prompt = ctk.CTkTextbox(self, height=80)
        self.prompt.pack(fill="x", padx=20, pady=5)
        self.prompt.insert("0.0", "Algo sano, bajo en colesterol, para esta noche")

        # M-12: filtros dietéticos
        diet_frame = ctk.CTkFrame(self, fg_color="transparent")
        diet_frame.pack(fill="x", padx=20, pady=(0, 5))
        ctk.CTkLabel(diet_frame, text="Dietas:").pack(side="left", padx=(0, 8))
        self.diet_vars: dict[str, ctk.BooleanVar] = {}
        for key in DIETARY_RESTRICTIONS:
            var = ctk.BooleanVar(value=False)
            self.diet_vars[key] = var
            label = key.replace("_", " ").capitalize()
            ctk.CTkCheckBox(diet_frame, text=label, variable=var, width=110).pack(side="left", padx=4)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 10), anchor="w")
        self.generate_btn = ctk.CTkButton(
            btn_row, text="✨ Generar recetas y carrito", command=self._on_generate
        )
        self.generate_btn.pack(side="left", padx=(0, 8))
        self.export_md_btn = ctk.CTkButton(
            btn_row,
            text="📄 Exportar recetas (.md)",
            command=self._on_export_md,
            state="disabled",
            fg_color="#356",
            hover_color="#234",
        )
        self.export_md_btn.pack(side="left")

        # M-02: barra de progreso
        self.progress = ctk.CTkProgressBar(self, width=400)
        self.progress.set(0)
        self.progress.pack(padx=20, pady=(0, 4), anchor="w")

        self.status = ctk.CTkLabel(self, text="", text_color="gray")
        self.status.pack(anchor="w", padx=20)

        self.results = ctk.CTkScrollableFrame(self, label_text="Resultados")
        self.results.pack(fill="both", expand=True, padx=20, pady=10)

    def _on_generate(self):
        prompt = self.prompt.get("1.0", "end").strip()
        if not prompt:
            return
        days = int(self.days_var.get())
        personas = int(self.personas_var.get())
        difficulty = self.difficulty_var.get()
        servings = personas * 2  # 1 comida + 1 cena por persona y día
        restrictions = [k for k, v in self.diet_vars.items() if v.get()]
        self._last_prompt = prompt
        history_add(prompt)
        self._refresh_history_menu()
        self.generate_btn.configure(state="disabled", text="Generando…")
        self.export_md_btn.configure(state="disabled")
        self.progress.set(0)
        self.status.configure(text="Pidiendo ideas a Gemini…")
        threading.Thread(
            target=self._worker,
            args=(prompt, days, servings, self.fresh_var.get(), restrictions, personas, difficulty),
            daemon=True,
        ).start()
        self.after(80, self._drain_progress)

    def _drain_progress(self):
        """Drena la cola de progreso y actualiza barra + status."""
        try:
            while True:
                fraction, msg = self._progress_q.get_nowait()
                self.progress.set(fraction)
                if msg:
                    self.status.configure(text=msg)
        except queue.Empty:
            pass
        # Solo seguir drenando si el botón sigue desactivado
        if str(self.generate_btn.cget("state")) == "disabled":
            self.after(80, self._drain_progress)

    def _emit_progress(self, fraction: float, msg: str):
        self._progress_q.put((max(0.0, min(1.0, fraction)), msg))

    def _refresh_history_menu(self):
        entries = history_load()
        if not entries:
            self.history_menu.configure(values=["(vacío)"])
            self.history_var.set("(vacío)")
            return
        labels = [e["text"] for e in entries]
        self.history_menu.configure(values=labels)
        self.history_var.set(labels[0])

    def _on_history_pick(self, choice: str):
        if choice == "(vacío)":
            return
        self.prompt.delete("1.0", "end")
        self.prompt.insert("0.0", choice)

    def _on_history_clear(self):
        history_clear()
        self._refresh_history_menu()

    def _worker(self, prompt: str, days: int, servings: int, fresh: bool, restrictions: list[str] | None = None, personas: int = 1, difficulty: str = "cualquiera"):
        try:
            pantry = PantryStore()
            avoid = AvoidStore()

            # Paso 1: pedir recetas
            self._emit_progress(0.1, "Pidiendo recetas a Gemini…")
            plan = recipe_engine.generate_meal_plan(
                prompt, days=days, servings=servings,
                restrictions=restrictions or [],
                personas=personas, difficulty=difficulty,
            )
            self._last_plan = plan
            recipes = plan.get("days", [])

            all_ingredients = []
            for day in recipes:
                meals = day.get("meals") or [day]  # compat hacia atrás
                for m in meals:
                    for ing in m.get("ingredients", []):
                        all_ingredients.append(ing["name"])

            # Paso 2: consolidar
            self._emit_progress(0.35, "Consolidando ingredientes…")
            shopping = recipe_engine.consolidate_shopping_list(recipes)
            raw_names = [it["name"] for it in shopping] or all_ingredients
            raw_quantities = [parse_quantity(it.get("quantity", "")) for it in shopping] or [1.0] * len(all_ingredients)
            raw_units = [extract_unit(it.get("quantity", "")) for it in shopping] or [""] * len(all_ingredients)

            # Dedupe por nombre normalizado: si Gemini devuelve "quinoa" 5 veces
            # con "1kg" cada una, sumamos a una sola entrada de 5kg.
            merged: dict[str, dict] = {}
            for name, qty, unit in zip(raw_names, raw_quantities, raw_units):
                # Dedupe por nombre normalizado: si Gemini devuelve "quinoa" 5 veces
                # con "1kg" cada una, sumamos a una sola entrada de 5kg.
                key = name.lower().strip()
                if key in merged:
                    merged[key]["quantity"] += qty
                    merged[key]["unit"] = merged[key].get("unit") or unit
                    merged[key]["display_name"] = merged[key].get("display_name", name)
                else:
                    merged[key] = {"display_name": name, "quantity": qty, "unit": unit}

            # APLICAR PANTRY ANTES del dedupe por core. Asi "filetes de salmon" y
            # "lomos de salmon" (con primary_core distinto "filetes" vs "lomos")
            # se filtran individualmente por fuzzy contra "salmon" en pantry,
            # sin depender de que compartan primary_core.
            items_for_matcher_pre = [v["display_name"] for v in merged.values()]
            quantities_pre = [
                v["quantity"] for v in merged.values()
            ]

            # Normalizar al final: g/ml > 5 -> kg/litro
            items_for_matcher = [
                v["display_name"] for v in merged.values()
            ]
            quantities = [
                normalize_for_cart(v["quantity"], v.get("unit", ""), v["display_name"])
                for v in merged.values()
            ]

            avoided = [it for it in items_for_matcher if avoid.contains(it)]
            items_after_avoid = [it for it in items_for_matcher if not avoid.contains(it)]
            qtys_after_avoid = [
                q for it, q in zip(items_for_matcher, quantities) if not avoid.contains(it)
            ]
            skipped_pantry = [it for it in items_after_avoid if pantry.contains(it)]
            items_after_pantry = pantry.filter_out(items_after_avoid)
            qtys_after_pantry = [
                q for it, q in zip(items_after_avoid, qtys_after_avoid) if not pantry.contains(it)
            ]

            # Paso 3: matching en Mercadona
            total_to_match = max(1, len(items_after_pantry))
            self._emit_progress(0.55, f"Buscando 0/{total_to_match} en Mercadona…")
            matched = product_matcher.match_many(items_after_pantry, fresh=fresh)

            # Dedupe post-match: si dos productos matched son el mismo 'core'
            # (ej. 3 vinagres distintos) consolidar en uno. El primero gana.
            matched = product_matcher.dedupe_by_core(matched)

            # Paso 4: rellenar carrito
            cart_log = get_logger("cart")
            added = 0
            for i, (ing_name, product, qty) in enumerate(zip(items_after_pantry, matched, qtys_after_pantry), 1):
                frac = 0.55 + 0.40 * (i / total_to_match)
                self._emit_progress(frac, f"Rellenando carrito {i}/{total_to_match}…")
                if product and product.get("id"):
                    self.cart.add(product, quantity=qty, origin=ing_name)
                    cart_log.info(
                        "cart + %s x %s (id=%s) from '%s'",
                        qty, product.get("name"), product.get("id"), ing_name,
                    )
                    added += 1
                    self.after(0, self.on_cart_updated)

            self._emit_progress(1.0, "Listo")
            self.after(0, lambda: self._render_results(
                recipes, shopping, matched,
                skipped_pantry, avoided, items_after_pantry,
            ))
        except Exception as e:
            err = e
            self.after(0, lambda: self.status.configure(text=f"Error: {err}", text_color="red"))
            self._emit_progress(0.0, f"Error: {err}")
        finally:
            self.after(0, lambda: self.generate_btn.configure(state="normal", text="✨ Generar recetas y carrito"))
            self.after(0, lambda: self.export_md_btn.configure(
                state=("normal" if self._last_plan else "disabled")
            ))

    def _render_results(self, recipes, shopping, matched, skipped_pantry=None, avoided=None, items_after_pantry=None):
        for w in self.results.winfo_children():
            w.destroy()

        skipped_pantry = skipped_pantry or []
        avoided = avoided or []
        items_after_pantry = items_after_pantry or []
        total_recipes = sum(len(d.get("meals") or [d]) for d in recipes)
        parts = [f"Listo · {len(recipes)} días / {total_recipes} recetas · carrito: {self.cart.total():.2f} €"]
        if skipped_pantry:
            parts.append(f"pantry: {len(skipped_pantry)}")
        if avoided:
            parts.append(f"avoid: {len(avoided)}")
        self.status.configure(text=" · ".join(parts))
        self.on_cart_updated()

        if skipped_pantry:
            box = ctk.CTkFrame(self.results)
            box.pack(fill="x", padx=10, pady=8)
            ctk.CTkLabel(
                box, text="🏺 Saltados (ya en pantry):",
                font=ctk.CTkFont(weight="bold"),
            ).pack(anchor="w", padx=10, pady=(8, 0))
            txt = "\n".join(f"  • {x}" for x in skipped_pantry)
            ctk.CTkLabel(box, text=txt, justify="left").pack(anchor="w", padx=20, pady=(0, 8))

        if avoided:
            box = ctk.CTkFrame(self.results)
            box.pack(fill="x", padx=10, pady=8)
            ctk.CTkLabel(
                box, text="🚫 Saltados (en avoid):",
                font=ctk.CTkFont(weight="bold"),
            ).pack(anchor="w", padx=10, pady=(8, 0))
            txt = "\n".join(f"  • {x}" for x in avoided)
            ctk.CTkLabel(box, text=txt, justify="left").pack(anchor="w", padx=20, pady=(0, 8))

        if items_after_pantry:
            box = ctk.CTkFrame(self.results)
            box.pack(fill="x", padx=10, pady=8)
            ctk.CTkLabel(
                box, text=f"🛒 Vas a comprar ({len(items_after_pantry)}):",
                font=ctk.CTkFont(weight="bold"),
            ).pack(anchor="w", padx=10, pady=(8, 0))
            txt = "\n".join(f"  • {x}" for x in items_after_pantry)
            ctk.CTkLabel(box, text=txt, justify="left", wraplength=900).pack(
                anchor="w", padx=20, pady=(0, 8)
            )

        for day in recipes:
            day_box = ctk.CTkFrame(self.results)
            day_box.pack(fill="x", padx=10, pady=10)
            weekday = day.get("weekday", "")
            title = f"Día {day.get('day')}" + (f" · {weekday.capitalize()}" if weekday else "")
            ctk.CTkLabel(
                day_box, text=title, font=ctk.CTkFont(size=15, weight="bold"),
            ).pack(anchor="w", padx=10, pady=(8, 4))

            meals = day.get("meals") or [day]  # compat: estructura plana antigua
            for r in meals:
                self._render_meal(day_box, r)

    def _render_meal(self, parent, r: dict):
        meal = (r.get("meal") or "").upper()
        meal_emoji = "🍽" if meal == "COMIDA" else "🌙" if meal == "CENA" else "🍴"
        box = ctk.CTkFrame(parent)
        box.pack(fill="x", padx=20, pady=4)
        title = f"{meal_emoji} {meal} — {r.get('title', 'Receta')}"
        ctk.CTkLabel(box, text=title, font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10, pady=(6, 0)
        )
        meta_bits = []
        if r.get("difficulty"):
            meta_bits.append(f"dificultad: {r['difficulty']}")
        if r.get("prep_minutes"):
            meta_bits.append(f"~{r['prep_minutes']} min")
        if meta_bits:
            ctk.CTkLabel(
                box, text="  ·  ".join(meta_bits), text_color="gray",
            ).pack(anchor="w", padx=10)
        if r.get("description"):
            ctk.CTkLabel(box, text=r["description"], text_color="gray").pack(
                anchor="w", padx=10
            )
        steps = r.get("steps", [])
        if steps:
            ctk.CTkLabel(box, text="Pasos:", font=ctk.CTkFont(weight="bold")).pack(
                anchor="w", padx=10, pady=(6, 0)
            )
            for s in steps:
                ctk.CTkLabel(
                    box, text=f"  • {s}", justify="left", wraplength=900,
                ).pack(anchor="w", padx=20)
        ings = r.get("ingredients", [])
        if ings:
            ctk.CTkLabel(box, text="Ingredientes:", font=ctk.CTkFont(weight="bold")).pack(
                anchor="w", padx=10, pady=(6, 0)
            )
            txt = "\n".join(f"  • {i['name']} — {i.get('quantity','')}" for i in ings)
            ctk.CTkLabel(box, text=txt, justify="left").pack(anchor="w", padx=20, pady=(0, 8))

    def _on_export_md(self):
        if not self._last_plan:
            messagebox.showinfo("Sin recetas", "Genera primero un plan de recetas.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown", "*.md")],
            initialfile="recetas.md",
        )
        if not path:
            return
        md = render_recipes_markdown(self._last_plan, prompt=self._last_prompt)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(md)
        except OSError as e:
            messagebox.showerror("Error", f"No se pudo escribir el archivo:\n{e}")
            return
        messagebox.showinfo("Exportado", f"Recetas guardadas en:\n{path}")
