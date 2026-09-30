# Vozdoo

**Habla y escribe. Pídele y te lo mejora.** Dictado por voz y asistente de
textos y prompts, gratis y 100 % en tu ordenador.

- **Dictar:** mantienes pulsada una tecla, hablas, sueltas, y el texto se
  escribe donde tengas el cursor (correo, documento, chat...).
- **Asistente:** con otra tecla le pides cosas en voz alta:
  *"optimiza prompt profesional"*, *"pasa esto a texto legal"*,
  *"hazlo persuasivo"*, *"conviértelo en un correo"*... y te lo devuelve
  listo para pegar.

Nada sale de tu ordenador: la voz la transcribe Whisper y los textos los
trabaja una IA local (Ollama). Sin cuentas, sin claves, sin coste por uso.

## Resumen rápido

**Instalar** (una línea; no hace falta tener nada instalado ni descargar
nada antes, lo baja todo de aquí):

| Sistema | Dónde | Pegar esto y pulsar Enter |
|---|---|---|
| Windows | PowerShell | `irm https://raw.githubusercontent.com/MHGRPM/ideo-vozdoo/main/install.ps1 \| iex` |
| Mac | Terminal | `curl -fsSL https://raw.githubusercontent.com/MHGRPM/ideo-vozdoo/main/install.sh \| bash` |
| Linux | Terminal | `curl -fsSL https://raw.githubusercontent.com/MHGRPM/ideo-vozdoo/main/install.sh \| bash` |

Unos 10 minutos la primera vez (descarga ~3 GB). Al final pregunta si
quieres que arranque solo al encender el ordenador y abre Vozdoo. Queda un
icono **Vozdoo** en el escritorio. Para actualizar, la misma línea.

**Funciones:**

| Qué | Cómo |
|---|---|
| Dictar | **Ctrl + Win** pulsado, hablas, sueltas: se escribe donde está el cursor |
| Asistente por voz | **Alt + Win** pulsado y dices la orden: "optimiza prompt profesional: ...", "pasa esto a texto legal", "hazlo persuasivo" |
| Sobre qué texto | El que digas tras la orden; si no, lo último dictado o copiado |
| 14 modos expertos | Prompt profesional, prompt de imagen, persuasivo, legal, formal, correo, LinkedIn, cercano, sencillo, en puntos, resumir, ampliar, inglés, corregir |
| Órdenes libres | Cualquier otra petición ("hazlo más gracioso", "ponlo en una tabla") |
| Mesa de trabajo | Panel para retocar, encadenar cambios y **Pegar donde estaba** |
| Menú | Botón derecho sobre la bola |
| Mover la bola | Arrástrala a cualquier sitio, en cualquier pantalla: se queda donde la dejes |
| Cerrar y volver a abrir | Botón derecho → **Cerrar** la esconde; **Ctrl + Win** o **Alt + Win** la vuelven a abrir. **Salir del todo** apaga Vozdoo (se abre desde el icono) |
| Chatear escribiendo | App de Ollama → modelo `vozdoo` |
| Privacidad | 100 % local, funciona sin internet una vez instalado |

(En Mac: Win = Cmd, Alt = Option.)

---

## Instalar (un solo paso)

El instalador lo pone todo: el programa, la IA local, el motor de voz y un
acceso directo. **No necesitas tener nada instalado antes.** Tarda unos
10 minutos la primera vez (descarga unos 3 GB); déjalo terminar.

### Windows

1. Pulsa la tecla **Windows**, escribe **PowerShell** y ábrelo.
2. Copia esta línea, pégala (clic derecho) y pulsa **Enter**:

```powershell
irm https://raw.githubusercontent.com/MHGRPM/ideo-vozdoo/main/install.ps1 | iex
```

> Otra forma: arriba en esta página, botón verde **Code → Download ZIP**,
> descomprímelo y haz doble clic en **`Instalar-Vozdoo.bat`**. Si Windows
> avisa de que "protegió tu PC", pulsa *Más información → Ejecutar de
> todas formas*.

### Mac

1. Abre **Terminal** (Cmd + Espacio, escribe "Terminal").
2. Copia esta línea, pégala y pulsa **Enter**:

```bash
curl -fsSL https://raw.githubusercontent.com/MHGRPM/ideo-vozdoo/main/install.sh | bash
```

La primera vez que lo abras, el Mac te pedirá permiso para el
**Micrófono** y para **Accesibilidad / Supervisión de entrada**. Acéptalos
en *Ajustes del Sistema → Privacidad y seguridad* y vuelve a abrir Vozdoo
desde *Aplicaciones*.

### Linux (Ubuntu, Debian, Fedora...)

1. Abre una **Terminal** (Ctrl + Alt + T).
2. Copia esta línea, pégala y pulsa **Enter** (te pedirá tu contraseña):

```bash
curl -fsSL https://raw.githubusercontent.com/MHGRPM/ideo-vozdoo/main/install.sh | bash
```

Al terminar, Vozdoo se abre solo y queda un icono **Vozdoo** en el
escritorio y en el menú de aplicaciones. El instalador te pregunta si
quieres que arranque solo al encender el ordenador.

**Para actualizar** a la última versión: repite el mismo paso. Conserva
tus ajustes.

---

## Usar

Verás una bola brillante en una esquina de la pantalla.

| Quiero... | Cómo |
|---|---|
| **Dictar** | Mantén pulsado **Ctrl + Win**, habla, suelta. Se escribe donde tengas el cursor. |
| **Pedirle algo al asistente** | Mantén pulsado **Alt + Win**, di la orden, suelta. |
| Ver todas las opciones | **Botón derecho** sobre la bola. |
| Moverla o cambiar su tamaño | Arrástrala / rueda del ratón encima. |

(En Mac, "Win" es la tecla **Cmd** y "Alt" es **Option**.)

### Qué le puedes pedir al asistente

Di la orden y, si quieres, el texto seguido:

> *"Optimiza prompt profesional: quiero un plan para captar clientes en
> el sector de la hostelería"*

> *"Pasa a persuasivo: nuestro programa ayuda a las tiendas a llevar el
> stock y facturar"*

Si **no dices el texto**, trabaja sobre lo último que dictaste o lo
último que copiaste (Ctrl + C). Por ejemplo: copias un párrafo de un
contrato, pulsas Alt + Win y dices *"ponlo sencillo"*.

| Dile... | Y hace |
|---|---|
| "optimiza prompt profesional", "mejora el prompt" | Un prompt completo para ChatGPT, Claude o Gemini: rol, objetivo, contexto, pasos, restricciones, formato y criterios de calidad |
| "prompt de imagen" | Un prompt para generar imágenes (en inglés, con su traducción) |
| "hazlo persuasivo", "que venda" | Texto comercial que convence, con llamada a la acción |
| "pásalo a texto legal", "tipo contrato" | Lenguaje jurídico formal y preciso |
| "más formal", "profesional" | Tono de trabajo, claro y educado |
| "conviértelo en un correo" | Correo listo para enviar, con asunto |
| "hazlo post de LinkedIn" | Publicación con gancho, párrafos cortos y pregunta final |
| "más cercano", "informal" | Tono amable y natural |
| "ponlo sencillo", "fácil" | Lenguaje claro que entiende cualquiera |
| "en puntos", "esquema" | Viñetas ordenadas |
| "resúmelo" / "amplíalo" | Más corto / más desarrollado |
| "tradúcelo al inglés" | Traducción profesional |
| "corrígelo" | Solo ortografía, acentos y puntuación |
| **Cualquier otra cosa** ("hazlo más gracioso", "ponlo en una tabla") | Lo hace tal cual se lo pidas |

El resultado aparece en un panel (**la mesa de trabajo**) donde puedes
retocarlo, seguir pidiéndole cambios (con botones, con "Más modos" o
escribiendo en *"Pídele otra cosa"*) y pulsar **Pegar donde estaba**.

Truco: también funciona con la tecla de dictar si empiezas la frase con la
orden ("optimiza prompt profesional...", "pasa esto a legal"). Si
simplemente dictas, se escribe tal cual.

**Cuánto tarda:** en un portátil normal, corregir o cambiar el tono de un
párrafo son 10-30 segundos; un prompt profesional largo, 1-2 minutos. El
panel te va contando los segundos y puedes cancelar cuando quieras.

### Chatear con el asistente

El instalador crea en Ollama un asistente llamado **vozdoo** con todo este
conocimiento. Si abres la app de **Ollama** y eliges el modelo `vozdoo`,
puedes chatear con él escribiendo, igual que con ChatGPT pero en local.

---

## Si algo no va

| Problema | Solución |
|---|---|
| No veo la bola | Pulsa Alt + Win: la trae a tu pantalla. Si no, abre Vozdoo desde el icono. |
| La tecla no hace nada (Linux) | Tu sesión puede ser Wayland. En la pantalla de inicio de sesión elige "Ubuntu en Xorg". |
| Escribe mal nombres o palabras técnicas | En el archivo `.env` de la carpeta Vozdoo cambia `VOZDOO_WHISPER_MODEL=small` por `medium`. |
| El asistente dice que falta la IA | Pulsa el botón **Instalar** del panel que aparece, o repite la instalación. |
| Va lento el asistente | Normal sin tarjeta gráfica. Con poca memoria (8 GB) pon `VOZDOO_LLM_MODEL=qwen2.5:3b-instruct` en `.env`. |
| Otra cosa | Mira el archivo `vozdoo.log` dentro de la carpeta Vozdoo y compártelo. |

Vozdoo se instala en la carpeta **Vozdoo** de tu usuario. Para
desinstalarlo, borra esa carpeta y el icono del escritorio.

---
---

## Detalles técnicos

### Qué instala

| Pieza | Para qué |
|---|---|
| `uv` + Python 3.12 propio en `Vozdoo/.venv` | No toca ningún Python del sistema |
| `faster-whisper` (modelo `small`, ~250 MB) | Voz a texto, en CPU |
| Ollama + `qwen3:4b-instruct` (~2,5 GB) | La IA del asistente, local |
| Modelo `vozdoo` en Ollama | El mismo modelo con el conocimiento del asistente dentro, para chatear |
| PyQt6 | La bola, las burbujas y el panel |
| Linux: `libportaudio2`, `xclip`, `libxcb-cursor0` | Micrófono, portapapeles y ventanas Qt |

### Cómo funciona el asistente

- `polish_actions.py` — el conocimiento: cada modo es un "experto" con su
  propio prompt de sistema (ingeniero de prompts, copywriter, abogado,
  editor, traductor...) y las palabras con las que se le pide por voz.
  Añadir un modo nuevo es añadir una entrada aquí.
- `voice_commands.py` — entiende la orden hablada sin llamar al modelo
  (palabras clave, instantáneo): qué modo, sobre qué texto y cualquier
  matiz ("pásalo a LinkedIn *para inspirar a otros PMs*: ...").
- `llm_engine.py` — manda el prompt de sistema en su campo y el encargo
  aparte; mantiene el modelo cargado 30 min para que las siguientes
  órdenes empiecen al momento.
- `ollama_setup.py prepare <modelo>` — descarga el modelo y crea el
  asistente `vozdoo` (lo usa el instalador).

### Configuración (`.env`)

| Variable | Por defecto | Qué hace |
|---|---|---|
| `VOZDOO_HOTKEY` | `ctrl+win` | Tecla de dictar (`ctrl+alt+d`, `f9`...) |
| `VOZDOO_POLISH_HOTKEY` | `alt+win` | Tecla del asistente |
| `VOZDOO_WHISPER_MODEL` | `small` | `tiny`/`base`/`small`/`medium`/`large-v3` |
| `VOZDOO_WHISPER_LANGUAGE` | `es` | Idioma forzado |
| `VOZDOO_WHISPER_DEVICE` | `auto` | `auto`/`cpu`/`cuda` |
| `VOZDOO_MIC_DEVICE` | (vacío) | Índice de micro, ver `list_devices.py` |
| `VOZDOO_MAX_RECORDING_SECONDS` | `30` | Corte automático |
| `VOZDOO_AUTO_PASTE` | `true` | `false` = solo copia, no pega solo |
| `VOZDOO_LLM_MODEL` | `qwen3:4b-instruct` | Modelo de Ollama |
| `VOZDOO_LLM_HOST` | `http://localhost:11434` | URL de Ollama |
| `VOZDOO_LLM_API_KEY` | (vacío) | Si la rellenas, se usa tu API (OpenAI, Gemini...) en vez de Ollama |
| `VOZDOO_LLM_API_URL` | OpenAI | Endpoint compatible con chat completions |
| `VOZDOO_LLM_API_MODEL` | `gpt-4o-mini` | Modelo de la API |

Tras cambiar el `.env`, cierra Vozdoo (botón derecho → Cerrar) y vuelve a
abrirlo.

### Instalación manual (desarrolladores)

```bash
git clone https://github.com/MHGRPM/ideo-vozdoo.git
cd ideo-vozdoo
./start-vozdoo.sh          # Windows: .\start-vozdoo.ps1
```

`start-vozdoo.sh` / `.ps1` crean el entorno con el Python del sistema y
arrancan con la consola abierta (útil para ver el log). Ollama y el
modelo se instalan aparte (`ollama pull qwen3:4b-instruct`) o desde el
panel que aparece la primera vez que se usa el asistente.

Tests: `.venv/bin/python -m pip install -r requirements-dev.txt && .venv/bin/python -m pytest`.

### Notas

- Un solo Vozdoo a la vez: si ya está abierto, el acceso directo no abre
  otro.
- Whisper con GPU NVIDIA (CUDA 12): `VOZDOO_WHISPER_DEVICE=cuda`. Si
  falla, cae solo a CPU.
- Wayland puro sin XWayland: `pynput` no puede leer teclas globales;
  usar sesión X11.
