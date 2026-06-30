"""
Vista: lista de la compra (lo que ya tengo en casa).
"""
from core.user_lists import PantryStore
from ui.simple_list_view import SimpleListView


class PantryView(SimpleListView):
    def __init__(self, master, cart=None, on_cart_updated=None):
        super().__init__(
            master,
            store=PantryStore(),
            title="🏺 Pantry (ya tengo en casa)",
            hint='Ingredientes que ya tienes: "arroz", "aceite", "sal". Se restarán de la lista de la compra.',
            empty_msg="(lista vacía)",
        )
