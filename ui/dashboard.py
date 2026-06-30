"""
Dashboard / shell principal con sidebar. Mantiene el Cart compartido y
cambia entre vistas.
"""
import customtkinter as ctk

from core.cart_engine import Cart
from adapters import mercadona_cli
from ui.recipe_view import RecipeView
from ui.cart_view import CartView
from ui.search_view import SearchView


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


VIEWS = {
    "recipe": ("🥗 Recipe Generator", RecipeView),
    "cart": ("🛒 Cart", CartView),
    "search": ("🔍 Product Search", SearchView),
}


class Dashboard(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI Grocery Planner · Mercadona")
        self.geometry("1100x750")
        self.minsize(900, 600)

        self.cart = Cart()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(
            self.sidebar,
            text="🧠 AI Grocery\nPlanner",
            font=ctk.CTkFont(size=20, weight="bold"),
            justify="left",
        ).pack(padx=20, pady=(24, 4), anchor="w")
        ctk.CTkLabel(self.sidebar, text="Powered by Gemini + mercadona-cli", text_color="gray").pack(
            padx=20, anchor="w"
        )

        nav = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav.pack(fill="x", padx=12, pady=20)

        self._nav_btns: dict[str, ctk.CTkButton] = {}
        for key, (label, _) in VIEWS.items():
            b = ctk.CTkButton(
                nav, text=label, anchor="w", height=40,
                command=lambda k=key: self.show(k),
                fg_color="transparent", text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray30"),
            )
            b.pack(fill="x", pady=2)
            self._nav_btns[key] = b

        self.cart_summary = ctk.CTkLabel(self.sidebar, text="", justify="left", text_color="gray")
        self.cart_summary.pack(side="bottom", padx=20, pady=20, anchor="w")

        self.status_cli = ctk.CTkLabel(self.sidebar, text="", text_color="gray")
        self.status_cli.pack(side="bottom", padx=20, anchor="w")

        self.container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.container.grid(row=0, column=1, sticky="nsew")
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self._frames: dict[str, ctk.CTkFrame] = {}
        for key, (_, factory) in VIEWS.items():
            if key == "cart":
                frame = factory(self.container, self.cart)
            else:
                frame = factory(self.container, self.cart, self._on_cart_updated)
            frame.grid(row=0, column=0, sticky="nsew")
            self._frames[key] = frame

        self.show("recipe")
        self._check_cli()

    def _check_cli(self):
        if mercadona_cli.is_available():
            self.status_cli.configure(text="● mercadona CLI OK", text_color="#5d5")
        else:
            self.status_cli.configure(
                text="● mercadona CLI no encontrado\n  npm i -g @ivorpad/mercadona",
                text_color="#e95",
            )

    def show(self, key: str):
        frame = self._frames[key]
        frame.tkraise()
        for k, b in self._nav_btns.items():
            b.configure(fg_color=("#1f6aa5" if k == key else "transparent"))
        if key == "cart" and hasattr(frame, "refresh"):
            frame.refresh()

    def _on_cart_updated(self):
        n = len(self.cart.items)
        total = self.cart.total()
        self.cart_summary.configure(text=f"🛒 {n} productos\n💰 {total:.2f} €")
        cart_frame = self._frames.get("cart")
        if cart_frame and hasattr(cart_frame, "refresh"):
            cart_frame.refresh()
