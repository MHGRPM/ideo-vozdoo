#!/usr/bin/env bash
# Instalador de Vozdoo para Mac y Linux. Lo deja todo listo:
# el programa, su Python, la IA local (Ollama + modelo + asistente),
# el motor de voz y un acceso directo. No hace falta tener nada instalado.
#
# Uso (pegar en una terminal):
#   curl -fsSL https://raw.githubusercontent.com/MHGRPM/ideo-vozdoo/main/install.sh | bash
#
# Para actualizar, se lanza otra vez el mismo comando: conserva tus ajustes.
set -euo pipefail

REPO_TGZ="https://github.com/MHGRPM/ideo-vozdoo/archive/refs/heads/main.tar.gz"
MODEL="${VOZDOO_LLM_MODEL:-qwen3:4b-instruct}"
OLLAMA_HOST_URL="http://localhost:11434"
OS="$(uname)"

say()  { printf '\n\033[1;35m==> %s\033[0m\n' "$*"; }
info() { printf '    %s\n' "$*"; }
warn() { printf '\n\033[1;33m[!] %s\033[0m\n' "$*"; }

ask_yes() {
    # Con "curl | bash" la entrada es el propio script: se pregunta a la terminal.
    local answer=""
    # La pregunta se escribe en la propia terminal: si no hay terminal
    # (instalación desatendida) se da por buena la respuesta "sí".
    if { printf '\n    %s [S/n] ' "$1" >/dev/tty; } 2>/dev/null; then
        read -r answer </dev/tty || answer=""
    fi
    case "$answer" in n|N|no|No|NO) return 1 ;; *) return 0 ;; esac
}

ollama_up() { curl -fsS -m 2 "$OLLAMA_HOST_URL/api/tags" >/dev/null 2>&1; }

wait_ollama() {
    for _ in $(seq 1 60); do
        ollama_up && return 0
        sleep 1
    done
    return 1
}

# ---------------------------------------------------------------------------
say "Instalando Vozdoo (tarda unos minutos la primera vez; déjalo terminar)"

# 1. Carpeta del programa ----------------------------------------------------
SCRIPT_PATH="${BASH_SOURCE[0]:-}"
if [ -n "$SCRIPT_PATH" ] && [ -f "$(dirname "$SCRIPT_PATH")/vozdoo_core.py" ]; then
    DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
    info "Usando la carpeta: $DIR"
else
    DIR="$HOME/Vozdoo"
    say "Descargando Vozdoo en $DIR"
    TMP="$(mktemp -d)"
    curl -fsSL "$REPO_TGZ" | tar -xz -C "$TMP"
    mkdir -p "$DIR"
    # Copiar encima conserva .env (tus ajustes) y .venv (lo ya instalado).
    cp -R "$TMP"/ideo-vozdoo-main/. "$DIR"/
    rm -rf "$TMP"
fi
cd "$DIR"

# 2. Piezas del sistema (solo Linux: Mac ya las trae) --------------------------
if [ "$OS" = "Linux" ]; then
    if command -v apt-get >/dev/null 2>&1; then
        APT_PKGS="curl libportaudio2 xclip libxcb-cursor0 libxkbcommon-x11-0 libxcb-icccm4 libxcb-keysyms1 libxcb-image0 libxcb-render-util0"
        MISSING=""
        for pkg in $APT_PKGS; do
            dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q "ok installed" || MISSING="$MISSING $pkg"
        done
        if [ -n "$MISSING" ]; then
            say "Instalando piezas del sistema (te pedirá tu contraseña)"
            # Los avisos de otros repositorios del ordenador (Chrome, Yarn...)
            # no afectan: por eso no se para si "update" se queja.
            sudo apt-get update -qq 2>/dev/null || true
            if ! sudo apt-get install -y -qq $MISSING >/dev/null; then
                # Lo típico: una instalación anterior del sistema se quedó a
                # medias. Se repara y se reintenta una vez.
                info "El sistema tenía una instalación a medias; reparándola..."
                sudo dpkg --configure -a >/dev/null 2>&1 || true
                sudo apt-get install -y -qq $MISSING >/dev/null \
                    || warn "No se pudieron instalar:$MISSING. Prueba en una terminal: sudo dpkg --configure -a && sudo apt-get install -y$MISSING"
            fi
        fi
    else
        say "Instalando piezas del sistema (te pedirá tu contraseña)"
        if command -v dnf >/dev/null 2>&1; then
            sudo dnf install -y -q portaudio xclip xcb-util-cursor xcb-util-wm \
                xcb-util-keysyms xcb-util-image xcb-util-renderutil libxkbcommon-x11 \
                || warn "No se pudieron instalar algunas piezas del sistema."
        elif command -v pacman >/dev/null 2>&1; then
            sudo pacman -S --needed --noconfirm portaudio xclip xcb-util-cursor \
                xcb-util-wm xcb-util-keysyms xcb-util-image xcb-util-renderutil \
                || warn "No se pudieron instalar algunas piezas del sistema."
        else
            warn "No reconozco tu Linux. Instala a mano: portaudio, xclip y xcb-util-cursor."
        fi
    fi
fi

# 3. Python propio de Vozdoo (no toca el Python de tu sistema) -----------------
say "Preparando Python"
if ! command -v uv >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/uv" ]; then
    curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null
fi
UV="$(command -v uv || echo "$HOME/.local/bin/uv")"

PY="$DIR/.venv/bin/python"
if ! "$PY" -c 'import sys; sys.exit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
    rm -rf "$DIR/.venv"
    "$UV" venv --seed --quiet --python 3.12 "$DIR/.venv"
fi

say "Instalando los componentes de Vozdoo"
"$UV" pip install --quiet --python "$PY" -r requirements.txt
info "Hecho."

[ -f .env ] || cp .env.example .env

# 4. IA local: Ollama + modelo + asistente --------------------------------------
say "Preparando la IA local (Ollama)"
if [ "$OS" = "Darwin" ]; then
    if [ ! -d "/Applications/Ollama.app" ] && [ ! -d "$HOME/Applications/Ollama.app" ] \
        && ! command -v ollama >/dev/null 2>&1; then
        info "Descargando Ollama..."
        TMP="$(mktemp -d)"
        curl -fsSL -o "$TMP/Ollama.zip" https://ollama.com/download/Ollama-darwin.zip
        unzip -q "$TMP/Ollama.zip" -d "$TMP"
        if ! mv "$TMP/Ollama.app" /Applications/ 2>/dev/null; then
            mkdir -p "$HOME/Applications"
            mv "$TMP/Ollama.app" "$HOME/Applications/"
        fi
        rm -rf "$TMP"
    fi
    ollama_up || open -a Ollama || true
else
    if ! command -v ollama >/dev/null 2>&1; then
        curl -fsSL https://ollama.com/install.sh | sh
    fi
    if ! ollama_up; then
        (nohup ollama serve >/dev/null 2>&1 &) || true
    fi
fi

if wait_ollama; then
    info "Descargando el modelo de IA ($MODEL, unos 2,5 GB; solo la primera vez)..."
    "$PY" ollama_setup.py prepare "$MODEL" || warn "No se pudo preparar el modelo. Vozdoo te ofrecerá instalarlo al usarlo."
else
    warn "Ollama no ha arrancado. Vozdoo te ofrecerá instalarlo la primera vez que le pidas algo."
fi

# 5. Motor de voz (Whisper), para que el primer dictado sea inmediato -----------
say "Descargando el motor de voz (solo la primera vez)"
"$PY" - <<'PYEOF' || warn "Se descargará al abrir Vozdoo."
import logging
logging.disable(logging.WARNING)
from faster_whisper import WhisperModel
WhisperModel("small", device="cpu", compute_type="int8")
print("    Hecho.")
PYEOF

# 6. Acceso directo y arranque automático ---------------------------------------
say "Creando el acceso directo"
if [ "$OS" = "Darwin" ]; then
    APP="$HOME/Applications/Vozdoo.app"
    mkdir -p "$HOME/Applications"
    rm -rf "$APP"
    osacompile -o "$APP" -e "do shell script \"cd '$DIR' && nohup ./.venv/bin/python vozdoo_core.py >/dev/null 2>&1 &\""
    info "Creado Vozdoo en tu carpeta Aplicaciones."
    if ask_yes "¿Quieres que Vozdoo se abra solo al encender el Mac?"; then
        osascript -e "tell application \"System Events\" to make login item at end with properties {path:\"$APP\", hidden:true}" >/dev/null 2>&1 || true
    fi
else
    DESKTOP_ENTRY="[Desktop Entry]
Type=Application
Name=Vozdoo
Comment=Dictado por voz y asistente de textos con IA local
Exec=\"$DIR/.venv/bin/python\" \"$DIR/vozdoo_core.py\"
Path=$DIR
Icon=$DIR/assets/icon/vozdoo.png
Terminal=false
Categories=Utility;"
    mkdir -p "$HOME/.local/share/applications"
    printf '%s\n' "$DESKTOP_ENTRY" > "$HOME/.local/share/applications/vozdoo.desktop"
    DESK="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
    if [ -d "$DESK" ]; then
        printf '%s\n' "$DESKTOP_ENTRY" > "$DESK/vozdoo.desktop"
        chmod +x "$DESK/vozdoo.desktop"
        gio set "$DESK/vozdoo.desktop" metadata::trusted true 2>/dev/null || true
    fi
    info "Creado Vozdoo en el menú de aplicaciones y en el escritorio."
    if ask_yes "¿Quieres que Vozdoo se abra solo al encender el ordenador?"; then
        mkdir -p "$HOME/.config/autostart"
        printf '%s\n' "$DESKTOP_ENTRY" > "$HOME/.config/autostart/vozdoo.desktop"
    fi
fi

# 7. Arrancar ------------------------------------------------------------------
if [ "${VOZDOO_NO_LAUNCH:-}" != "1" ]; then
    say "¡Listo! Abriendo Vozdoo..."
    (cd "$DIR" && nohup ./.venv/bin/python vozdoo_core.py >/dev/null 2>&1 &)
fi

cat <<'EOF'

    Verás una bola brillante en una esquina de la pantalla. Así se usa:

    DICTAR       Mantén pulsado Ctrl + Win, habla y suelta.
                 El texto se escribe donde tengas el cursor.

    ASISTENTE    Mantén pulsado Alt + Win y pide lo que quieras:
                   "Optimiza prompt profesional: quiero un plan de ventas..."
                   "Pasa esto a texto legal"
                   "Hazlo más persuasivo"
                 Si no dices el texto, usa lo último que dictaste o copiaste.

    MÁS OPCIONES Botón derecho sobre la bola.

EOF
if [ "$OS" = "Darwin" ]; then
    cat <<'EOF'
    MAC: la primera vez te pedirá permiso para el Micrófono y para
    Accesibilidad / Supervisión de entrada. Acéptalos (Ajustes del Sistema >
    Privacidad y seguridad) y vuelve a abrir Vozdoo desde Aplicaciones.

EOF
fi
