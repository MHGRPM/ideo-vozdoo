import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pynput import keyboard as pkb

from vozdoo_core import parse_hotkey, hotkeys_overlap


def test_parse_single_key():
    assert parse_hotkey("f9") == frozenset({pkb.Key.f9})


def test_parse_modifier_only_combo():
    assert parse_hotkey("ctrl+win") == frozenset({"ctrl", "cmd"})


def test_parse_combo_with_letter():
    assert parse_hotkey("ctrl+alt+d") == frozenset(
        {"ctrl", "alt", pkb.KeyCode.from_char("d")}
    )


def test_parse_unknown_key_returns_none():
    assert parse_hotkey("ctrl+notakey") is None


def test_hotkeys_overlap_true_when_subset():
    normal = parse_hotkey("ctrl+win")
    polish = parse_hotkey("ctrl+alt+win")
    assert hotkeys_overlap(normal, polish) is True


def test_hotkeys_overlap_false_when_disjoint_enough():
    normal = parse_hotkey("ctrl+win")
    polish = parse_hotkey("alt+win")
    assert hotkeys_overlap(normal, polish) is False
