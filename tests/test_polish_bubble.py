import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from polish_bubble import PRESET_INSTRUCTIONS

EXPECTED_PRESETS = {"Más formal", "Mejorar prompt", "Corregir", "Resumir"}


def test_preset_instructions_has_expected_keys():
    assert set(PRESET_INSTRUCTIONS.keys()) == EXPECTED_PRESETS


def test_preset_instructions_are_non_empty_strings():
    for instruction in PRESET_INSTRUCTIONS.values():
        assert isinstance(instruction, str)
        assert len(instruction) > 10
