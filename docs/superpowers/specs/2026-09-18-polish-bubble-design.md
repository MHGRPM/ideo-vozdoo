# Vozdoo: dictar + pulir con IA (burbuja flotante)

Fecha: 2026-09-18
Estado: aprobado, pendiente de implementación (v1)

## Objetivo

Añadir un segundo modo de dictado que, además de transcribir, deja
reescribir el texto con un LLM (más formal, mejorar un prompt, corregir,
resumir, o una instrucción personalizada dicha por voz) antes de pegarlo,
sin tocar el flujo de dictado instantáneo que ya existe y que el equipo
ya usa.

## Alcance de v1

Dentro:
- Segundo hotkey ("dictar + pulir"), independiente del hotkey normal.
- Burbuja flotante (tkinter) con presets + instrucción personalizada por voz.
- Motor de IA: Ollama local por defecto; si el usuario configura una API
  key propia (OpenAI o compatible, incluida Gemini vía su capa de
  compatibilidad OpenAI), se usa esa en vez de Ollama.
- Botón de instalación automática de Ollama con un clic cuando no está
  presente y no hay API key configurada.
- Revisión del resultado antes de pegar (Pegar / Descartar / Reintentar).

Fuera de v1 (descartado explícitamente):
- Automatizar Gemini vía el navegador con la sesión de Google Workspace
  de la empresa. Motivo: frágil (depende de que Chrome esté abierto y de
  que Google no cambie el DOM de la web) y riesgo de infringir los
  términos de servicio de Gemini al automatizar la interfaz web en vez de
  usar una API. La opción de API key personal cubre la misma necesidad
  (mejor calidad que el modelo local) sin ese riesgo.

## Flujo

1. Usuario mantiene pulsado `VOZDOO_POLISH_HOTKEY` (default `alt+win`), habla, suelta.
2. Se transcribe con el mismo pipeline de Whisper ya existente.
3. Se abre la burbuja cerca del cursor:
   - Texto transcrito (solo lectura)
   - Botones preset: "Más formal", "Mejorar prompt", "Corregir", "Resumir"
   - Botón 🎤 "Instrucción personalizada": mantener con el ratón + hablar
     (reutiliza `AudioBuffer`/`transcribe` de `vozdoo_core.py`)
4. Al elegir una acción, se llama al motor de IA (Ollama o API key) con
   la instrucción + el texto original. Estado "Pensando..." con cancelar.
5. Resultado en la burbuja con: **Pegar** (mismo mecanismo de
   copiar-al-portapapeles + simular Ctrl+V ya existente),
   **Descartar** (cierra sin pegar), **Reintentar** (vuelve al paso 3 con
   el texto original).
6. Si no hay Ollama corriendo y no hay API key: la burbuja muestra un
   aviso con botón "Instalar Ollama automáticamente".

## Componentes (ficheros nuevos, no se toca el flujo de dictado normal)

- `llm_engine.py`: interfaz `polish(text, instruction) -> str` con dos
  implementaciones:
  - `OllamaEngine`: llama a `POST {VOZDOO_LLM_HOST}/api/generate` (o
    `/api/chat`) con `VOZDOO_LLM_MODEL` (default `qwen2.5:3b-instruct`:
    responde rápido en CPU y sin fase de "pensamiento" larga, a
    diferencia de modelos de razonamiento como qwen3.5 que tardan
    minutos en tareas cortas como estas).
  - `ApiKeyEngine`: llama a `POST {VOZDOO_LLM_API_URL}` (formato chat
    completions estilo OpenAI) con `VOZDOO_LLM_API_KEY` y
    `VOZDOO_LLM_API_MODEL`. Sirve para OpenAI, Gemini (vía su endpoint
    compatible) o cualquier proveedor que hable ese mismo formato.
  - Selección automática: si `VOZDOO_LLM_API_KEY` no está vacío, se usa
    `ApiKeyEngine`; si no, `OllamaEngine`.
- `polish_bubble.py`: ventana `tkinter` con la máquina de estados de
  arriba (transcribiendo / eligiendo acción / pensando / resultado /
  instalar Ollama).
- `ollama_setup.py`: detecta si Ollama responde en `VOZDOO_LLM_HOST`;
  si no, ofrece instalarlo:
  - Linux/Mac: ejecuta el instalador oficial
    (`curl -fsSL https://ollama.com/install.sh | sh`) en una ventana de
    terminal visible (puede pedir contraseña de sudo, necesita TTY).
  - Windows: descarga y lanza el instalador oficial
    (`OllamaSetup.exe`); investigar en implementación si admite un modo
    silencioso (flags tipo Inno Setup `/VERYSILENT`) — si no, el usuario
    verá el asistente gráfico oficial y tendrá que darle a "Siguiente".
  - Tras instalar: `ollama pull {VOZDOO_LLM_MODEL}` con progreso visible.
- Cambios mínimos en `vozdoo_core.py`: registrar el segundo hotkey y
  extraer `paste_text` a un módulo compartido si hace falta reutilizarlo
  desde `polish_bubble.py`.

## Configuración nueva (`.env`)

| Variable | Por defecto | Qué hace |
|---|---|---|
| `VOZDOO_POLISH_HOTKEY` | `alt+win` | Hotkey de "dictar + pulir" |
| `VOZDOO_LLM_API_KEY` | (vacío) | Si se rellena, usa esta API en vez de Ollama |
| `VOZDOO_LLM_API_URL` | endpoint de OpenAI | Cambiar para Gemini u otro proveedor compatible |
| `VOZDOO_LLM_API_MODEL` | `gpt-4o-mini` | Modelo a usar en esa API |
| `VOZDOO_LLM_MODEL` | `qwen2.5:3b-instruct` | Modelo local si no hay API key |
| `VOZDOO_LLM_HOST` | `http://localhost:11434` | Host de Ollama |

## Manejo de errores

- Ollama no responde y no hay API key → aviso + botón instalar.
- Ollama responde pero el modelo no está descargado → se lanza
  `ollama pull` con progreso, no falla en silencio.
- API key inválida o error de red → mensaje de error en la burbuja,
  sugerencia de revisar `.env`.
- Fallos del micrófono/Whisper en el flujo de "pulir" → igual que hoy,
  pero visibles en la burbuja en vez de solo en el log.

## Riesgos conocidos, aceptados

- El auto-instalador de Ollama en Windows puede no ser 100% silencioso
  (ver arriba).
- `tkinter` requiere una sesión gráfica (mismo requisito que ya existe
  hoy para `pynput` — no añade una limitación nueva). En Linux,
  `tkinter` es un paquete del sistema aparte (`python3-tk`), no viene
  con `python3`/`python3-venv` — hay que añadirlo a los requisitos del
  README.
- El botón de instrucción personalizada por voz añade una segunda
  grabación de audio anidada dentro del flujo — hay que evitar
  colisiones con el `AudioBuffer` único que ya existe en
  `vozdoo_core.py` (se resuelve en el plan de implementación).
- `VOZDOO_HOTKEY` y `VOZDOO_POLISH_HOTKEY` no pueden solaparse: si el
  conjunto de teclas de uno contiene todas las del otro (p.ej.
  `ctrl+win` dentro de `ctrl+alt+win`), pulsar el combo largo dispara
  primero el corto a medio camino. Por eso el default de
  `VOZDOO_POLISH_HOTKEY` es `alt+win` (no `ctrl+alt+win`): no comparte
  todas las teclas de `ctrl+win` en ningún orden de pulsación. Se añade
  una validación al arrancar que rechaza cualquier configuración donde
  se solapen.
