"""Tests del historial de prompts."""
from core import prompt_history


def test_add_returns_history(tmp_data_dir):
    entries = prompt_history.add("algo sano")
    assert len(entries) == 1
    assert entries[0]["text"] == "algo sano"
    assert "ts" in entries[0]


def test_add_empty_is_noop(tmp_data_dir):
    prompt_history.clear()
    entries = prompt_history.add("   ")
    assert entries == []


def test_add_moves_to_front_and_dedupes(tmp_data_dir):
    prompt_history.clear()
    prompt_history.add("primero")
    prompt_history.add("segundo")
    prompt_history.add("primero")
    entries = prompt_history.load()
    assert entries[0]["text"] == "primero"
    assert entries[1]["text"] == "segundo"
    assert len(entries) == 2


def test_dedupe_case_insensitive(tmp_data_dir):
    prompt_history.clear()
    prompt_history.add("Algo Sano")
    prompt_history.add("algo sano")
    entries = prompt_history.load()
    assert len(entries) == 1


def test_caps_at_max(tmp_data_dir):
    prompt_history.clear()
    for i in range(15):
        prompt_history.add(f"prompt {i}")
    entries = prompt_history.load()
    assert len(entries) == 10
    assert entries[0]["text"] == "prompt 14"


def test_clear_empties(tmp_data_dir):
    prompt_history.add("x")
    prompt_history.clear()
    assert prompt_history.load() == []


def test_persistence(tmp_data_dir):
    prompt_history.add("persiste")
    entries = prompt_history.load()
    assert entries[0]["text"] == "persiste"
