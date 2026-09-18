# Vozdoo

Dictado por voz local, tipo WisprFlow pero gratis y 100% local: mantienes
pulsada una tecla, hablas, sueltas, y el texto transcrito se pega donde
tengas el cursor (o se copia al portapapeles).

Nada sale de tu ordenador: la transcripción corre en local con
[faster-whisper](https://github.com/SYSTAN/faster-whisper). No hay claves
de API, no hay nube, no hay coste por uso.

Sin LLM, sin asistente, sin nada más: solo escucha y escribe lo que dices.

## Instalación

Requiere Python 3.10+.

**Windows:**
```powershell
.\start-vozdoo.ps1
```

**Linux / Mac:**
```bash
./start-vozdoo.sh
```

El script crea el entorno virtual, instala dependencias y copia
`.env.example` a `.env` la primera vez. Luego arranca Vozdoo.

La primerísima vez tardará ~30-60s descargando el modelo Whisper `small`
(244MB) a `~/.cache/huggingface/`. Las siguientes veces es instantáneo.

### Linux: portapapeles

`pyperclip` necesita una utilidad de portapapeles del sistema. Si el copiar
al portapapeles falla, instala una:
```bash
sudo apt install xclip     # o: sudo apt install xsel
```
En Wayland: `wl-clipboard`.

## Uso

1. Mantén pulsados **Ctrl + Win** (por defecto)
2. Habla
3. Suelta
4. El texto aparece pegado donde tuvieras el cursor (o en el portapapeles,
   según `VOZDOO_AUTO_PASTE`)

## Configuración (`.env`)

| Variable | Por defecto | Qué hace |
|---|---|---|
| `VOZDOO_HOTKEY` | `ctrl+win` | Tecla o combo (`ctrl+alt+d`, `f9`...) |
| `VOZDOO_WHISPER_MODEL` | `small` | `tiny`/`base`/`small`/`medium`/`large-v3` |
| `VOZDOO_WHISPER_LANGUAGE` | `es` | Idioma forzado |
| `VOZDOO_WHISPER_DEVICE` | `auto` | `auto`/`cpu`/`cuda` |
| `VOZDOO_MIC_DEVICE` | (vacío) | Índice de micro, ver `list_devices.py` |
| `VOZDOO_MAX_RECORDING_SECONDS` | `30` | Corte automático |
| `VOZDOO_AUTO_PASTE` | `true` | `false` = solo copia, no pega solo |

Si tu micro por defecto no es el correcto, ejecuta:
```bash
python list_devices.py
```
y pon el número que te interese en `VOZDOO_MIC_DEVICE`.

## Notas sobre el modelo

- `small` (244MB) va bien en CPU en portátiles normales.
- Si tienes GPU NVIDIA con drivers CUDA 12.x, `VOZDOO_WHISPER_DEVICE=cuda`
  baja la latencia notablemente. Si tu CUDA es 13.x puede fallar
  (`cublas64_12.dll`) — el script cae solo a CPU en ese caso.
- Si notáis errores de transcripción con nombres propios o jerga interna,
  subid a `medium` — más lento pero más preciso.

## Sobre el hotkey

El parser soporta tanto combos hechos solo de teclas modificadoras (como
el `ctrl+win` que usamos de default: se dispara al tener las dos pulsadas
a la vez y se corta al soltar cualquiera) como combos con una letra
(`ctrl+alt+d`) o teclas sueltas (`f9`), por si prefieres cambiarlo en tu
`.env`.

## Posibles mejoras futuras (no aplicadas, para valorar)

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
