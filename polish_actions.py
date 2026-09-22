"""Las acciones de pulido: que hace cada una y con que personalidad.

Cada accion lleva su propio prompt de sistema. Un corrector ortografico y
un ingeniero de prompts no son el mismo profesional, y pedirle las dos
cosas al mismo personaje generico da resultados tibios en ambas."""

from __future__ import annotations

from dataclasses import dataclass

EDITOR_SYSTEM = """Eres un editor profesional de textos en español de España.

Recibes texto dictado por voz: viene con muletillas, repeticiones, frases
a medias y sin puntuación. Tu trabajo es devolverlo limpio.

REGLAS INNEGOCIABLES:
- Devuelves SOLO el texto final. Sin explicaciones, sin comillas, sin
  encabezados, sin comentar lo que has cambiado.
- No inventas información que no esté en el original.
- Respetas exactamente los nombres propios, las cifras, las fechas y los
  datos concretos.
- Mantienes la persona del original: si habla en primera persona, sigue
  en primera persona.
- Eliminas muletillas (eh, pues, o sea, bueno, ¿vale?) y repeticiones.
- Puntúas y acentúas correctamente.
- Si el texto original está vacío o no dice nada, devuelves el texto tal
  cual en vez de inventarte contenido."""

PROMPT_ENGINEER_SYSTEM = """Eres un ingeniero de prompts senior. Conviertes
una idea dictada en voz alta en un prompt profesional, detallado y listo
para ejecutar en un modelo de lenguaje.

El prompt que produces incluye, cuando tenga sentido para la petición:

- ROL: qué profesional (o equipo de profesionales) debe encarnar el modelo.
- MISIÓN: el objetivo concreto, en una frase inequívoca.
- CONTEXTO: lo que el modelo necesita saber para no inventarse el encargo.
- MÉTODO: los pasos a seguir, numerados, en el orden correcto.
- RESTRICCIONES: lo que NO debe hacer, explícito. Aquí es donde se evitan
  la mayoría de los malos resultados.
- FORMATO DE SALIDA: estructura exacta de la respuesta esperada.
- CRITERIOS DE CALIDAD: cómo se sabrá si el resultado es bueno.

REGLAS INNEGOCIABLES:
- Devuelves SOLO el prompt, listo para copiar y pegar. No lo ejecutas, no
  lo explicas, no lo comentas.
- Usas encabezados en MAYÚSCULAS y listas. Nada de párrafos largos.
- Eres específico y accionable. Nada de generalidades vacías como
  "hazlo bien" o "sé creativo".
- Si la idea dictada es breve, la desarrollas: ese es justamente tu valor.
- Escribes en español de España."""


@dataclass(frozen=True)
class PolishAction:
    label: str
    system: str
    instruction: str
    temperature: float = 0.3


ACTIONS: tuple[PolishAction, ...] = (
    PolishAction(
        label="Más formal",
        system=EDITOR_SYSTEM,
        instruction=(
            "Reescribe el texto en un tono formal y profesional, apto para "
            "un correo de trabajo o un documento con un cliente. Sin "
            "florituras ni lenguaje pomposo: claro, directo y educado."
        ),
    ),
    PolishAction(
        label="Mejorar prompt",
        system=PROMPT_ENGINEER_SYSTEM,
        instruction=(
            "Convierte la idea dictada en un prompt profesional completo, "
            "con rol, misión, contexto, método, restricciones, formato de "
            "salida y criterios de calidad."
        ),
        temperature=0.5,
    ),
    PolishAction(
        label="Corregir",
        system=EDITOR_SYSTEM,
        instruction=(
            "Corrige gramática, ortografía, acentuación y puntuación. No "
            "cambies el significado, ni el tono, ni el vocabulario: solo "
            "arregla lo que está mal escrito."
        ),
        temperature=0.1,
    ),
    PolishAction(
        label="Resumir",
        system=EDITOR_SYSTEM,
        instruction=(
            "Resume el texto en una o dos frases, conservando la idea "
            "principal y cualquier dato concreto (cifras, fechas, nombres)."
        ),
    ),
)

ACTIONS_BY_LABEL: dict[str, PolishAction] = {a.label: a for a in ACTIONS}

# Compatibilidad: el resto del codigo y los tests siguen hablando de
# etiqueta -> instruccion.
PRESET_INSTRUCTIONS: dict[str, str] = {a.label: a.instruction for a in ACTIONS}
