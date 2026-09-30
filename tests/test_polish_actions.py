import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from polish_actions import (
    ACTIONS,
    MENU_ACTIONS,
    PRESET_INSTRUCTIONS,
    assistant_system_prompt,
    free_action,
)

CORE_PRESETS = {"Más formal", "Mejorar prompt", "Corregir", "Persuasivo", "Legal"}


def test_core_presets_exist():
    assert CORE_PRESETS <= set(PRESET_INSTRUCTIONS.keys())


def test_preset_instructions_are_non_empty_strings():
    for instruction in PRESET_INSTRUCTIONS.values():
        assert isinstance(instruction, str)
        assert len(instruction) > 10


def test_every_action_can_be_asked_by_voice():
    for action in ACTIONS:
        assert action.keywords, action.label
        assert action.system.strip(), action.label


def test_labels_are_unique():
    labels = [a.label for a in ACTIONS]
    assert len(labels) == len(set(labels))


def test_menu_is_short_enough_for_the_bubble_fan():
    assert 3 <= len(MENU_ACTIONS) <= 6


def test_free_action_uses_spoken_instruction():
    action = free_action("  hazlo más gracioso ")
    assert action.instruction == "hazlo más gracioso"
    assert action.system.strip()


def test_assistant_prompt_lists_every_mode():
    prompt = assistant_system_prompt()
    for action in ACTIONS:
        assert action.label in prompt
