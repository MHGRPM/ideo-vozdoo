"""Entender órdenes habladas: "optimiza prompt profesional: quiero...",
"pasa esto a texto legal", "hazlo más persuasivo", "tradúcelo al inglés".

De cada frase saca dos cosas: QUÉ modo aplicar y SOBRE QUÉ texto. Si la
orden no trae texto ("pasa esto a legal"), el contenido queda vacío y el
orbe usa lo último que dictaste o lo que tengas copiado.

Todo es local y determinista (palabras clave), sin llamar al modelo: la
orden se entiende al instante y el modelo solo trabaja una vez."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from polish_actions import ACTIONS, PolishAction, free_action

# Palabras de relleno que Whisper suele dejar al principio.
_LEAD_FILLERS = re.compile(
    r"^(?:[\s,.;:¡!¿?]*(?:oye|vale|venga|bueno|vozdoo|voz ?do|por favor|porfa|"
    r"ahora|a ver|mira|eh|em)\b)*[\s,.;:¡!¿?]*"
)

# Verbos con los que empieza una orden. Sin tildes: se compara normalizado.
_VERBS = (
    "optimiza optimizame optimizalo optimizar mejora mejorame mejoralo mejorar "
    "convierte conviertelo convierteme convertir pasa pasalo pasame pasar "
    "reescribe reescribelo reescribeme reescribir redacta redactame redactalo "
    "redactar transforma transformalo transformar haz hazlo hazme hacer cambia "
    "cambialo pon ponlo ponme ponle escribe escribeme escribelo escribir "
    "genera generame generar crea creame crear dame traduce traducelo "
    "traduceme traducir resume resumelo resumeme resumir corrige corrigelo "
    "corregir revisa revisalo adapta adaptalo amplia amplialo desarrolla "
    "desarrollalo acorta acortalo dale vuelve modo quiero necesito prepara "
    "preparame"
).split()
_VERB_RE = re.compile(r"(?:" + "|".join(sorted(_VERBS, key=len, reverse=True)) + r")\b")

# Palabras de enlace entre la orden y el contenido: "...a legal EL SIGUIENTE
# TEXTO nuestro producto...". Se quitan del principio del contenido.
_CONNECTOR_RE = re.compile(
    r"^[\s,.:;¡!¿?\-]*(?:y\s+)?(?:a|al|en|de|del|el|la|lo|los|las|un|una|"
    r"este|esta|esto|estos|siguiente|texto|mensaje|modo|tono|formato|"
    r"version|lenguaje|lo que dice|que dice|sobre|mi|idea|parrafo)\b"
)

# Hasta dónde se buscan palabras clave cuando la orden no lleva dos puntos:
# más allá ya es contenido, y "lista" o "post" ahí no son una orden.
_COMMAND_WINDOW = 60

# Lo único que puede haber entre dos palabras clave para que cuenten como
# la misma orden ("prompt DE FORMA profesional", "texto legal Y formal").
_GLUE_RE = re.compile(
    r"^[\s,]*(?:(?:de|forma|manera|a|al|y|e|texto|modo|tono|en|mas|muy|un|una|"
    r"estilo|version)[\s,]*)*$"
)


@dataclass(frozen=True)
class VoiceCommand:
    action: PolishAction
    content: str      # vacío = usar lo último dictado o el portapapeles


def normalize(text: str) -> str:
    """Minúsculas y sin tildes, conservando la longitud carácter a carácter
    para poder recortar el texto original en las mismas posiciones."""
    out = []
    for ch in text.lower():
        base = unicodedata.normalize("NFD", ch)[:1] or ch
        out.append(base if len(base) == 1 else ch)
    return "".join(out)


def _keyword_patterns() -> list[tuple[re.Pattern, PolishAction, int]]:
    patterns = []
    for action in ACTIONS:
        for kw in action.keywords:
            pat = re.compile(r"(?<![a-z0-9])" + re.escape(kw) + r"(?![a-z0-9])")
            patterns.append((pat, action, len(kw)))
    return patterns


_KEYWORDS = _keyword_patterns()


def _strip_connectors(text: str) -> str:
    for _ in range(8):
        norm = normalize(text)
        m = _CONNECTOR_RE.match(norm)
        if not m or m.end() == 0:
            break
        text = text[m.end():]
    return text.strip(" \t\n,.:;-")


def parse_command(text: str, strict: bool = True) -> VoiceCommand | None:
    """Devuelve la orden reconocida o None si la frase es dictado normal.

    `strict=True` (dictado normal): solo es orden si empieza por un verbo
    de orden Y nombra un modo conocido. Así "pasa a recogerme a las ocho"
    se sigue escribiendo tal cual.

    `strict=False` (tecla del asistente): cualquier frase es una orden; si
    no nombra un modo conocido, la propia frase es la instrucción."""
    if not text or not text.strip():
        return None
    norm = normalize(text)
    lead = _LEAD_FILLERS.match(norm)
    start = lead.end() if lead else 0

    verb = _VERB_RE.match(norm, start)
    if strict and verb is None:
        return None
    cmd_start = verb.end() if verb else start

    colon = norm.find(":", cmd_start)
    if 0 <= colon <= cmd_start + 120:
        window_end = colon
    else:
        colon = -1
        window_end = min(len(norm), cmd_start + _COMMAND_WINDOW)

    matches = []
    for pat, action, length in _KEYWORDS:
        for m in pat.finditer(norm, start, window_end):
            matches.append((m.start(), -length, m.end(), action))
    matches.sort(key=lambda t: (t[0], t[1]))

    if not matches:
        if strict:
            return None
        if colon >= 0:
            instruction = text[start:colon].strip()
            content = text[colon + 1:].strip()
        else:
            instruction = text[start:].strip()
            content = ""
        return VoiceCommand(free_action(instruction), content)

    _, _, end, action = matches[0]
    # "optimiza el prompt de forma profesional": la orden se alarga sobre
    # las palabras clave que vienen pegadas, para no mandarlas como texto.
    for m_start, _, m_end, _ in matches[1:]:
        if m_start >= end and _GLUE_RE.match(norm[end:m_start]):
            end = m_end

    if colon >= 0:
        nuance = _strip_connectors(text[end:colon])
        content = text[colon + 1:].strip()
    else:
        nuance = ""
        content = _strip_connectors(text[end:])

    if nuance:
        action = PolishAction(
            label=action.label,
            system=action.system,
            instruction=f"{action.instruction} Matiz que pide el usuario: {nuance}.",
            temperature=action.temperature,
            keywords=action.keywords,
            in_menu=action.in_menu,
        )
    return VoiceCommand(action, content)
