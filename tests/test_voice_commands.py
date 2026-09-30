import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from voice_commands import normalize, parse_command


def test_normalize_keeps_length():
    text = "Pásalo a INGLÉS, señor"
    assert len(normalize(text)) == len(text)
    assert normalize(text) == "pasalo a ingles, senor"


@pytest.mark.parametrize(
    "spoken, label, content",
    [
        (
            "Optimiza prompt profesional: quiero un plan de marketing para una tienda",
            "Mejorar prompt",
            "quiero un plan de marketing para una tienda",
        ),
        (
            "Optimiza prompt profesional quiero un plan de marketing para una tienda",
            "Mejorar prompt",
            "quiero un plan de marketing para una tienda",
        ),
        ("Convierte esto a texto legal.", "Legal", ""),
        (
            "Pasa a persuasivo el siguiente texto: nuestro software ahorra tiempo",
            "Persuasivo",
            "nuestro software ahorra tiempo",
        ),
        (
            "Optimiza texto a persuasivo nuestro software ahorra 3 horas al día",
            "Persuasivo",
            "nuestro software ahorra 3 horas al día",
        ),
        ("Tradúcelo al inglés", "Inglés", ""),
        ("Resúmelo", "Resumir", ""),
        ("Oye, escribe un correo a Juan diciendo que llego tarde", "Correo", "Juan diciendo que llego tarde"),
        ("Hazme un prompt de imagen de un gato astronauta", "Imagen", "gato astronauta"),
        (
            "Optimiza el prompt de forma profesional: crea un agente",
            "Mejorar prompt",
            "crea un agente",
        ),
    ],
)
def test_recognised_orders(spoken, label, content):
    command = parse_command(spoken, strict=True)
    assert command is not None
    assert command.action.label == label
    assert command.content == content


@pytest.mark.parametrize(
    "spoken",
    [
        "Pasa a recogerme a las ocho",
        "Mañana tenemos una lista de tareas",
        "Hola equipo, os escribo para lo del contrato",
        "",
    ],
)
def test_normal_dictation_is_not_an_order(spoken):
    assert parse_command(spoken, strict=True) is None


def test_assistant_key_turns_anything_into_an_order():
    command = parse_command("Hazlo más gracioso", strict=False)
    assert command.action.label == "A medida"
    assert command.action.instruction == "Hazlo más gracioso"
    assert command.content == ""


def test_free_order_with_colon_splits_content():
    command = parse_command("Ponlo en forma de tabla: enero 100, febrero 200", strict=False)
    assert command.action.instruction == "Ponlo en forma de tabla"
    assert command.content == "enero 100, febrero 200"


def test_mode_named_without_verb_on_assistant_key():
    command = parse_command("Legal: si no paga en 30 días cortamos", strict=False)
    assert command.action.label == "Legal"
    assert command.content == "si no paga en 30 días cortamos"


def test_nuance_before_colon_goes_into_instruction():
    command = parse_command(
        "Pásalo a LinkedIn para inspirar a otros PMs: hoy cerramos el contrato", strict=True
    )
    assert command.action.label == "LinkedIn"
    assert "inspirar a otros PMs" in command.action.instruction
    assert command.content == "hoy cerramos el contrato"
