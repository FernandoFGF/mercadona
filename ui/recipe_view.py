"""
Vista: generación de recetas con Gemini y volcado al carrito.
"""
import threading
import customtkinter as ctk

from core import recipe_engine, product_matcher
from core.cart_engine import Cart, CartItem


class RecipeView(ctk.CTkFrame):
    def __init__(self, master, cart: Cart, on_cart_updated):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.cart = cart
        self.on_cart_updated = on_cart_updated
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

        opts = ctk.CTkFrame(self, fg_color="transparent")
        opts.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(opts, text="Días:").pack(side="left", padx=(0, 5))
        self.days_var = ctk.IntVar(value=1)
        ctk.CTkOptionMenu(opts, values=["1", "2", "3", "5", "7"], variable=self.days_var, width=70).pack(
            side="left", padx=(0, 15)
        )

        ctk.CTkLabel(opts, text="Raciones/día:").pack(side="left", padx=(0, 5))
        self.serv_var = ctk.IntVar(value=2)
        ctk.CTkOptionMenu(opts, values=["1", "2", "3", "4"], variable=self.serv_var, width=70).pack(
            side="left", padx=(0, 15)
        )

        ctk.CTkLabel(opts, text="Solo frescos:").pack(side="left", padx=(0, 5))
        self.fresh_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(opts, text="", variable=self.fresh_var).pack(side="left")

        self.prompt = ctk.CTkTextbox(self, height=80)
        self.prompt.pack(fill="x", padx=20, pady=5)
        self.prompt.insert("0.0", "Algo sano, bajo en colesterol, para esta noche")

        self.generate_btn = ctk.CTkButton(
            self, text="✨ Generar recetas y carrito", command=self._on_generate
        )
        self.generate_btn.pack(padx=20, pady=10, anchor="w")

        self.status = ctk.CTkLabel(self, text="", text_color="gray")
        self.status.pack(anchor="w", padx=20)

        self.results = ctk.CTkScrollableFrame(self, label_text="Resultados")
        self.results.pack(fill="both", expand=True, padx=20, pady=10)

    def _on_generate(self):
        prompt = self.prompt.get("1.0", "end").strip()
        if not prompt:
            return
        days = int(self.days_var.get())
        servings = int(self.serv_var.get())
        self.generate_btn.configure(state="disabled", text="Generando…")
        self.status.configure(text="Pidiéndole ideas a Gemini…")
        threading.Thread(
            target=self._worker, args=(prompt, days, servings, self.fresh_var.get()), daemon=True
        ).start()

    def _worker(self, prompt: str, days: int, servings: int, fresh: bool):
        try:
            plan = recipe_engine.generate_meal_plan(prompt, days=days, servings=servings)
            recipes = plan.get("days", [])

            all_ingredients = []
            for r in recipes:
                for ing in r.get("ingredients", []):
                    all_ingredients.append(ing["name"])

            shopping = recipe_engine.consolidate_shopping_list(recipes)
            items_for_matcher = [it["name"] for it in shopping] or all_ingredients

            matched = product_matcher.match_many(items_for_matcher, fresh=fresh)

            for ing_name, product in zip(items_for_matcher, matched):
                if product and product.get("id"):
                    self.cart.add(product, quantity=1.0, origin=ing_name)

            self.after(0, lambda: self._render_results(recipes, shopping, matched))
        except Exception as e:
            err = e
            self.after(0, lambda: self.status.configure(text=f"Error: {err}", text_color="red"))
        finally:
            self.after(0, lambda: self.generate_btn.configure(state="normal", text="✨ Generar recetas y carrito"))

    def _render_results(self, recipes, shopping, matched):
        for w in self.results.winfo_children():
            w.destroy()

        self.status.configure(text=f"OK · {len(recipes)} recetas · carrito: {self.cart.total():.2f} €")
        self.on_cart_updated()

        for r in recipes:
            box = ctk.CTkFrame(self.results)
            box.pack(fill="x", padx=10, pady=8)
            ctk.CTkLabel(
                box,
                text=f"Día {r.get('day')} · {r.get('meal', '').upper()} — {r.get('title')}",
                font=ctk.CTkFont(weight="bold"),
            ).pack(anchor="w", padx=10, pady=(8, 0))
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
                    ctk.CTkLabel(box, text=f"  • {s}", justify="left", wraplength=900).pack(
                        anchor="w", padx=20
                    )
            ings = r.get("ingredients", [])
            if ings:
                ctk.CTkLabel(box, text="Ingredientes:", font=ctk.CTkFont(weight="bold")).pack(
                    anchor="w", padx=10, pady=(6, 0)
                )
                txt = "\n".join(f"  • {i['name']} — {i.get('quantity','')}" for i in ings)
                ctk.CTkLabel(box, text=txt, justify="left").pack(anchor="w", padx=20, pady=(0, 8))
