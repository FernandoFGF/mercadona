"""Tests del bus de eventos y de la sincronizacion pantry/avoid."""
import pytest

from core.event_bus import EventBus, default_bus
from core.user_lists import PantryStore, AvoidStore


def test_event_bus_on_off_emit():
    bus = EventBus()
    received = []
    bus.on("evt", lambda *a, **kw: received.append(a))
    bus.emit("evt", 1, 2, x=3)
    assert received == [(1, 2)]


def test_event_bus_off():
    bus = EventBus()
    received = []
    cb = lambda *a, **kw: received.append(a)
    bus.on("evt", cb)
    bus.off("evt", cb)
    bus.emit("evt", 1)
    assert received == []


def test_event_bus_handler_error_doesnt_break_others():
    bus = EventBus()
    received = []
    bus.on("evt", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    bus.on("evt", lambda: received.append("ok"))
    bus.emit("evt")
    assert received == ["ok"]


@pytest.fixture
def clean_bus():
    """Limpia los listeners del bus antes y despues del test."""
    saved = {k: list(v) for k, v in default_bus._listeners.items()}
    default_bus._listeners.clear()
    yield
    default_bus._listeners.clear()
    default_bus._listeners.update(saved)


def test_pantry_add_emits_event(clean_bus, tmp_data_dir):
    received = []
    default_bus.on("pantry_changed", lambda cls: received.append(cls))
    store = PantryStore()
    assert store.add("quinoa event test 1") is True
    assert received == ["PantryStore"]
    store.remove("quinoa event test 1")


def test_avoid_add_emits_event(clean_bus, tmp_data_dir):
    received = []
    default_bus.on("avoid_changed", lambda cls: received.append(cls))
    store = AvoidStore()
    assert store.add("marisco event test 1") is True
    assert received == ["AvoidStore"]
    store.remove("marisco event test 1")


def test_pantry_duplicate_does_not_emit(clean_bus, tmp_data_dir):
    received = []
    default_bus.on("pantry_changed", lambda cls: received.append(cls))
    store = PantryStore()
    store.add("dup event test 1")
    received.clear()
    # Segundo add del mismo termino no debe emitir
    assert store.add("dup event test 1") is False
    assert received == []
    store.remove("dup event test 1")
