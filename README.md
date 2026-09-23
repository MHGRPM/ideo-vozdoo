# Vozdoo

Dictado por voz local, tipo WisprFlow pero gratis y 100% local: mantienes
pulsada una tecla, hablas, sueltas, y el texto transcrito se pega donde
tengas el cursor (o se copia al portapapeles).

Nada sale de tu ordenador: la transcripción corre en local con
[faster-whisper](https://github.com/SYSTAN/faster-whisper). No hay claves
de API, no hay nube, no hay coste por uso. Sin LLM, sin asistente, sin
nada más: solo escucha y escribe lo que dices.

---

## Guía rápida

**Instalar (solo la primera vez):**

*Windows* — abre PowerShell y pega esto, línea por línea:
```powershell
git clone https://github.com/MHGRPM/ideo-vozdoo.git
cd ideo-vozdoo
.\start-vozdoo.ps1
```

*Linux* — abre una terminal y pega esto, línea por línea:
```bash
sudo apt install python3 python3-venv python3-pip git libportaudio2 xclip libxcb-cursor0
git clone https://github.com/MHGRPM/ideo-vozdoo.git
cd ideo-vozdoo
./start-vozdoo.sh
```

*Mac* — abre una terminal y pega esto, línea por línea:
```bash
brew install python3 portaudio git
git clone https://github.com/MHGRPM/ideo-vozdoo.git
cd ideo-vozdoo
./start-vozdoo.sh
```

La primera vez tarda 2-3 minutos descargando cosas — es normal, deja que
termine. Cuando veas el mensaje `Vozdoo listo...`, ya puedes usarlo.

**Usar:**

1. Mantén pulsado **Ctrl + Win**
2. Habla
3. Suelta
4. El texto sale escrito donde tuvieras el cursor

**Para pararlo:** `Ctrl+C` en esa misma ventana, o ciérrala.

**Para volver a usarlo otro día:** abre una terminal, entra en la carpeta
y vuelve a lanzar el mismo comando de instalación (`./start-vozdoo.sh` o
`.\start-vozdoo.ps1`) — esta vez arranca en segundos.

Si algo no funciona a la primera, sigue leyendo más abajo: está todo
explicado con más detalle y con soluciones a los problemas más comunes.

---

## 1. Antes de instalar (requisitos del sistema)

Necesitas Python 3.10 o superior y `git`. Comprueba si ya los tienes:

```bash
python3 --version   # o "python --version" en Windows
git --version
```

Si falta alguno, instálalo primero según tu sistema:

### Windows

1. Descarga Python desde https://www.python.org/downloads/ e instálalo.
   **Importante**: marca la casilla "Add python.exe to PATH" durante la
   instalación.
2. Instala Git desde https://git-scm.com/downloads (si no lo tienes ya).

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip git libportaudio2 libxcb-cursor0
```

- `python3-venv` es imprescindible: sin él, el script falla al crear el
  entorno virtual con un error tipo "ensurepip is not available".
- `libportaudio2` es necesario para que la librería que graba el
  micrófono (`sounddevice`) funcione.
- Además necesitas una utilidad de portapapeles (para pegar el texto
  automáticamente): instala **una** de estas dos, no hace falta ambas:
  ```bash
  sudo apt install xclip
  # o, alternativamente:
  sudo apt install xsel
  ```
  Si usas Wayland, instala `wl-clipboard` en su lugar.

### Mac

```bash
brew install python3 portaudio git
```

---

## 2. Instalación

Clona el repositorio y entra en la carpeta:

```bash
git clone https://github.com/MHGRPM/ideo-vozdoo.git
cd ideo-vozdoo
```

Lanza el instalador de tu sistema operativo:

**Windows** (PowerShell):
```powershell
.\start-vozdoo.ps1
```

**Linux / Mac**:
```bash
./start-vozdoo.sh
```

Si en Linux/Mac te da `Permission denied`, ejecútalo así en su lugar:
```bash
bash start-vozdoo.sh
```

### Qué hace el instalador y qué vas a ver

El script hace 4 cosas, y va imprimiendo en qué paso está:

1. `==> Creando entorno virtual...` — solo la primerísima vez.
2. `==> Instalando dependencias...` — **esto puede tardar 1-3 minutos** la
   primera vez porque descarga el motor de Whisper (varios cientos de MB).
   Vas a ver mucho texto de `pip` descargando paquetes: es normal, no está
   colgado.
3. `==> Creado .env con valores por defecto...` — solo la primera vez.
4. `==> Arrancando Vozdoo...` — descarga el modelo de voz (~244MB) la
   primera vez (otro medio minuto), luego arranca. Cuando veas:
   ```
   Vozdoo listo. 'ctrl+win' dicta y pega. 'alt+win' dicta y pulir con IA. Ctrl+C para salir.
   ```
   ya está listo para usar.

Las siguientes veces que lo arranques, todo esto es prácticamente
instantáneo (ya está todo descargado e instalado).

---

## 3. Uso

1. Mantén pulsados **Ctrl + Win** (hotkey por defecto)
2. Habla
3. Suelta
4. El texto aparece pegado donde tuvieras el cursor (o copiado al
   portapapeles, según `VOZDOO_AUTO_PASTE` — ver configuración abajo)

Para parar Vozdoo: `Ctrl+C` en la ventana donde lo lanzaste, o simplemente
cerrarla.

Para volver a arrancarlo otro día, repite el mismo comando
(`./start-vozdoo.sh` o `.\start-vozdoo.ps1`) desde dentro de la carpeta
`ideo-vozdoo`.

---

## El orbe: dictar y pulir con IA

Al arrancar Vozdoo aparece un orbe pequeño flotando en una esquina de la
pantalla. En reposo está quieto y no gasta nada; el vídeo solo se
reproduce mientras te está escuchando.

| Gesto | Qué hace |
|---|---|
| Mantener pulsado el orbe | Graba mientras lo sujetas. Al soltar, transcribe y te ofrece las acciones |
| Botón derecho | Abre las mini-burbujas. Con algo dictado, las acciones de IA; sin nada dictado, tamaño y salir |
| Arrastrar | Lo mueves donde quieras. Recuerda la posición para la próxima vez |
| Rueda del ratón | Lo hace más grande o más pequeño (de 28 a 140 px) |
| **Alt + Win** | Lo mismo que mantenerlo pulsado, pero desde el teclado |

Las acciones son: pegar tal cual, más formal, mejorar prompt, corregir y
resumir. Al elegir una, el texto pasa por la IA y aparece un panel donde
puedes **retocarlo antes de pegarlo**.

### El panel: la mesa de trabajo

Al elegir una acción aparece un panel oscuro con el resultado. Ahí puedes:

- **Editarlo a mano** antes de nada.
- **Encadenar acciones** sobre lo que ya hay: corregir, luego hacerlo más
  formal, luego resumir. Cada botón trabaja sobre el texto que ves, no
  sobre el original.
- **Pegar donde estabas** — el correo, el documento, el chat — con el
  botón de abajo.

Mientras la IA trabaja verás una barra de carga con los segundos que
lleva. En un portátil sin tarjeta gráfica, pulir una frase son unos 8
segundos y escribir un prompt profesional completo puede irse a 40. Si se
te hace largo, **Cancelar** te devuelve el panel al momento.

### La IA local (Ollama)

Vozdoo pule los textos con Ollama **en tu propio ordenador**. No se envía
nada a ningún servidor: ni tus dictados, ni los textos de tus clientes.

Si no lo tienes instalado, la primera vez que uses una acción de IA
aparecerá un panel que te lo explica y te lo instala con un botón, con la
descarga del modelo a la vista. También te enseña el comando por si
prefieres hacerlo tú:

```
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:3b-instruct
```

En Windows se descarga el instalador oficial de ollama.com y luego el
modelo.

El modelo por defecto (`qwen2.5:3b-instruct`, unos 2 GB) va rápido en
cualquier portátil. Si quieres más calidad y no te importa esperar,
cambia `VOZDOO_LLM_MODEL` en el `.env` por uno mayor, por ejemplo
`qwen2.5:7b-instruct`.

Si prefieres tu propia clave de API (OpenAI o Gemini), configúrala en
`.env` (`VOZDOO_LLM_API_KEY`) y se usará esa en su lugar, sin necesidad
de Ollama.

El dictado normal (`Ctrl + Win`) sigue funcionando igual y no depende del
orbe para nada: si PyQt6 no arranca en tu equipo, pierdes el orbe pero no
el dictado.

---

## 4. Configuración (`.env`)

El instalador crea un archivo `.env` la primera vez (copiado de
`.env.example`). Ábrelo con cualquier editor de texto para cambiar estos
valores:

| Variable | Por defecto | Qué hace |
|---|---|---|
| `VOZDOO_HOTKEY` | `ctrl+win` | Tecla o combo (`ctrl+alt+d`, `f9`...) |
| `VOZDOO_WHISPER_MODEL` | `small` | `tiny`/`base`/`small`/`medium`/`large-v3` |
| `VOZDOO_WHISPER_LANGUAGE` | `es` | Idioma forzado |
| `VOZDOO_WHISPER_DEVICE` | `auto` | `auto`/`cpu`/`cuda` |
| `VOZDOO_MIC_DEVICE` | (vacío) | Índice de micro, ver `list_devices.py` |
| `VOZDOO_MAX_RECORDING_SECONDS` | `30` | Corte automático |
| `VOZDOO_AUTO_PASTE` | `true` | `false` = solo copia, no pega solo |
| `VOZDOO_POLISH_HOTKEY` | `alt+win` | Tecla o combo para "dictar y pulir con IA" |
| `VOZDOO_LLM_API_KEY` | (vacío) | Si la rellenas, se usa tu API en vez de Ollama local |
| `VOZDOO_LLM_API_URL` | `https://api.openai.com/v1/chat/completions` | Endpoint de la API (OpenAI, Gemini vía capa de compatibilidad...) |
| `VOZDOO_LLM_API_MODEL` | `gpt-4o-mini` | Modelo a usar con la API key |
| `VOZDOO_LLM_MODEL` | `qwen2.5:3b-instruct` | Modelo de Ollama local (si no hay API key) |
| `VOZDOO_LLM_HOST` | `http://localhost:11434` | URL de Ollama local |

Si tu micro por defecto no es el correcto, con el entorno activado
ejecuta:
```bash
python list_devices.py
```
y pon el número que te interese en `VOZDOO_MIC_DEVICE`.

Tras cambiar el `.env`, tienes que parar Vozdoo (`Ctrl+C`) y volver a
arrancarlo para que se aplique.

---

## 5. Solución de problemas

**"ensurepip is not available" al crear el entorno virtual (Linux)**
Falta el paquete del sistema: `sudo apt install python3-venv`.

**Parece colgado en "Instalando dependencias..."**
Es normal la primera vez (1-3 minutos, descarga el motor de Whisper).
Si llevas más de 5 minutos sin ningún cambio en pantalla, corta con
`Ctrl+C` y vuelve a lanzar el script — suele ser un corte de red.

**`OSError` o "PortAudio library not found" al arrancar**
Falta la librería del sistema: `sudo apt install libportaudio2` (Linux)
o `brew install portaudio` (Mac).

**No pega el texto donde el cursor, o da error de portapapeles (Linux)**
Falta `xclip` o `xsel`: `sudo apt install xclip`. En Wayland,
`sudo apt install wl-clipboard`.

**El hotkey no reacciona a nada (Linux)**
Si tu sesión es Wayland puro (sin XWayland), la librería que detecta
teclas globales (`pynput`) puede no funcionar. Comprueba tu tipo de
sesión con `echo $XDG_SESSION_TYPE`. Si dice `wayland` y no funciona,
prueba a iniciar sesión en modo "Ubuntu en Xorg"/X11 desde la pantalla
de login.

**Se transcribe mal / no pilla nombres propios o jerga del equipo**
Sube el modelo a `medium` en `.env` (`VOZDOO_WHISPER_MODEL=medium`) —
más preciso, algo más lento.

**Quiero reinstalar desde cero**
Borra la carpeta `.venv` y el archivo `.env`, y vuelve a lanzar el
script:
```bash
rm -rf .venv .env
./start-vozdoo.sh
```

Si algo no está en esta lista, mira el mensaje de error completo en la
terminal (o en `vozdoo.log`) y compártelo para que se pueda añadir aquí.

---

## 6. Notas sobre el modelo

- `small` (244MB) va bien en CPU en portátiles normales.
- Si tienes GPU NVIDIA con drivers CUDA 12.x, `VOZDOO_WHISPER_DEVICE=cuda`
  baja la latencia notablemente. Si tu CUDA es 13.x puede fallar
  (`cublas64_12.dll`) — el script cae solo a CPU en ese caso.
- Si notáis errores de transcripción con nombres propios o jerga interna,
  subid a `medium` — más lento pero más preciso.

## 7. Sobre el hotkey

El parser soporta tanto combos hechos solo de teclas modificadoras (como
el `ctrl+win` que usamos de default: se dispara al tener las dos pulsadas
a la vez y se corta al soltar cualquiera) como combos con una letra
(`ctrl+alt+d`) o teclas sueltas (`f9`), por si prefieres cambiarlo en tu
`.env`.

## 8. Posibles mejoras futuras (no aplicadas, para valorar)

- **Bandeja del sistema / icono de estado**: ahora mismo corre en una
  ventana de terminal. Un icono en la bandeja (Windows/Linux) con
  indicador de "grabando" sería más cómodo para uso diario.
- **Autoarranque**: registrar como tarea programada / servicio de usuario
  para que arranque solo al iniciar sesión.
- **Modelo compartido pre-descargado**: si se instala en varios equipos
  del equipo, descargar el modelo una vez y distribuirlo (o usar un share
  de red) ahorra esos 244MB por persona.
- **Vocabulario propio**: `faster-whisper` acepta un `initial_prompt` con
  términos frecuentes (nombres propios, jerga interna del equipo) para
  mejorar precisión en esas palabras.
- **Push-to-talk vs. wake word**: esto es solo push-to-talk (mantener
  pulsado). Manos libres con palabra de activación ("wake word") es un
  proyecto aparte, con más piezas (reconocimiento always-on, un modelo de
  lenguaje local, etc.), no solo Whisper.
