"""
Bus de eventos simple para sincronizar vistas (pantry/avoid) cuando
se modifican desde otra vista (search, etc.).
"""


class EventBus:
    def __init__(self):
        self._listeners: dict[str, list] = {}

    def on(self, event: str, callback) -> None:
        self._listeners.setdefault(event, []).append(callback)

    def off(self, event: str, callback) -> None:
        if event in self._listeners:
            try:
                self._listeners[event].remove(callback)
            except ValueError:
                pass

    def emit(self, event: str, *args, **kwargs) -> None:
        for cb in list(self._listeners.get(event, [])):
            try:
                cb(*args, **kwargs)
            except Exception:
                pass


default_bus = EventBus()

