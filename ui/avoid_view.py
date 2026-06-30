"""
Vista: lista de ingredientes que NO quiero comprar.
"""
from core.user_lists import AvoidStore
from ui.simple_list_view import SimpleListView


class AvoidView(SimpleListView):
    def __init__(self, master, cart=None, on_cart_updated=None):
        super().__init__(
            master,
            store=AvoidStore(),
            title="🚫 Avoid (no quiero comprar)",
            hint='Ingredientes a evitar: "marisco", "frutos secos", "perejil". Se omitirán al buscar productos.',
            empty_msg="(lista vacía)",
        )
