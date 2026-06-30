"""
Dashboard / shell principal con sidebar. Mantiene el Cart compartido y
cambia entre vistas.
"""
import customtkinter as ctk

from core.cart_engine import Cart
from core.settings_store import get as settings_get
from adapters import mercadona_cli
from ui.recipe_view import RecipeView
from ui.cart_view import CartView
from ui.search_view import SearchView
from ui.pantry_view import PantryView
from ui.avoid_view import AvoidView
from ui.settings_dialog import SettingsDialog


ctk.set_appearance_mode(str(settings_get("appearance_mode")))
ctk.set_default_color_theme("blue")


VIEWS = {
    "recipe": ("🥗 Recipe Generator", RecipeView),
    "cart": ("🛒 Cart", CartView),
    "search": ("🔍 Product Search", SearchView),
    "pantry": ("🏺 Pantry", PantryView),
    "avoid": ("🚫 Avoid", AvoidView),
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

        # M-05: bloque destacado de precio en vivo
        self.price_box = ctk.CTkFrame(self.sidebar)
        self.price_box.pack(side="bottom", fill="x", padx=12, pady=(8, 4))
        ctk.CTkLabel(
            self.price_box, text="Total estimado", text_color="gray",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=12, pady=(8, 0))
        self.price_lbl = ctk.CTkLabel(
            self.price_box, text="0.00 €",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        self.price_lbl.pack(anchor="w", padx=12, pady=(0, 4))
        self.cart_summary = ctk.CTkLabel(
            self.price_box, text="0 productos", text_color="gray", justify="left",
        )
        self.cart_summary.pack(anchor="w", padx=12, pady=(0, 8))

        self.status_cli = ctk.CTkLabel(self.sidebar, text="", text_color="gray")
        self.status_cli.pack(side="bottom", padx=20, anchor="w")

        # M-14: botón de ajustes; M-17: switch de tema
        tools = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        tools.pack(side="bottom", fill="x", padx=12, pady=8)
        self.theme_var = ctk.StringVar(value=str(settings_get("appearance_mode")))
        self.theme_switch = ctk.CTkSwitch(
            tools, text="Tema claro", command=self._toggle_theme,
            variable=self.theme_var, onvalue="light", offvalue="dark",
        )
        self.theme_switch.pack(side="left", padx=4)
        ctk.CTkButton(tools, text="⚙", width=36, command=self._open_settings).pack(side="right")

        self.container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.container.grid(row=0, column=1, sticky="nsew")
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self._frames: dict[str, ctk.CTkFrame] = {}
        for key, (_, factory) in VIEWS.items():
            if key in ("cart", "pantry", "avoid"):
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
        self.price_lbl.configure(text=f"{total:.2f} €")
        self.cart_summary.configure(text=f"{n} producto(s)")
        cart_frame = self._frames.get("cart")
        if cart_frame and hasattr(cart_frame, "refresh"):
            cart_frame.refresh()

    def _toggle_theme(self):
        mode = self.theme_var.get()
        ctk.set_appearance_mode(mode)

    def _open_settings(self):
        SettingsDialog(self, on_appearance_change=self._apply_theme)

    def _apply_theme(self, mode: str):
        ctk.set_appearance_mode(mode)
        self.theme_var.set(mode)
