# Instalador de Vozdoo para Windows. Lo deja todo listo:
# el programa, su Python, la IA local (Ollama + modelo + asistente),
# el motor de voz y un acceso directo en el escritorio.
# No hace falta tener nada instalado.
#
# Uso: doble clic en "Instalar-Vozdoo.bat", o pegar en PowerShell:
#   irm https://raw.githubusercontent.com/MHGRPM/ideo-vozdoo/main/install.ps1 | iex
#
# Para actualizar, se lanza otra vez: conserva tus ajustes.

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"   # Invoke-WebRequest va 10 veces mas rapido sin barra
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$RepoZip = "https://github.com/MHGRPM/ideo-vozdoo/archive/refs/heads/main.zip"
$Model = if ($env:VOZDOO_LLM_MODEL) { $env:VOZDOO_LLM_MODEL } else { "qwen3:4b-instruct" }
$OllamaUrl = "http://localhost:11434"

function Say($text)  { Write-Host ""; Write-Host "==> $text" -ForegroundColor Magenta }
function Info($text) { Write-Host "    $text" }
function Warn($text) { Write-Host ""; Write-Host "[!] $text" -ForegroundColor Yellow }

function Test-Ollama {
    try { Invoke-RestMethod -Uri "$OllamaUrl/api/tags" -TimeoutSec 2 | Out-Null; return $true }
    catch { return $false }
}

function Wait-Ollama {
    for ($i = 0; $i -lt 60; $i++) {
        if (Test-Ollama) { return $true }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Ask-Yes($question) {
    $answer = Read-Host "    $question [S/n]"
    return -not ($answer -match '^(n|no)$')
}

Say "Instalando Vozdoo (tarda unos minutos la primera vez; dejalo terminar)"

# 1. Carpeta del programa ------------------------------------------------------
if ($PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot "vozdoo_core.py"))) {
    $Dir = $PSScriptRoot
    Info "Usando la carpeta: $Dir"
} else {
    $Dir = Join-Path $env:USERPROFILE "Vozdoo"
    Say "Descargando Vozdoo en $Dir"
    $tmp = Join-Path $env:TEMP ("vozdoo-" + [guid]::NewGuid())
    New-Item -ItemType Directory -Path $tmp | Out-Null
    Invoke-WebRequest -Uri $RepoZip -OutFile "$tmp\vozdoo.zip" -UseBasicParsing
    Expand-Archive -Path "$tmp\vozdoo.zip" -DestinationPath $tmp -Force
    New-Item -ItemType Directory -Path $Dir -Force | Out-Null
    # Copiar encima conserva .env (tus ajustes) y .venv (lo ya instalado).
    Copy-Item -Path "$tmp\ideo-vozdoo-main\*" -Destination $Dir -Recurse -Force
    Remove-Item -Recurse -Force $tmp
}
Set-Location $Dir

# 2. Python propio de Vozdoo (no toca ningun Python que ya tengas) -------------
Say "Preparando Python"
$uvPaths = @("$env:USERPROFILE\.local\bin", "$env:USERPROFILE\.cargo\bin")
$env:Path = ($uvPaths -join ";") + ";" + $env:Path
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex" | Out-Null
}
$uv = (Get-Command uv).Source

$py = Join-Path $Dir ".venv\Scripts\python.exe"
$pyOk = $false
if (Test-Path $py) {
    try {
        & $py -c "import sys; sys.exit(sys.version_info < (3, 10))"
        $pyOk = ($LASTEXITCODE -eq 0)
    } catch { $pyOk = $false }
}
if (-not $pyOk) {
    if (Test-Path "$Dir\.venv") { Remove-Item -Recurse -Force "$Dir\.venv" }
    & $uv venv --seed --quiet --python 3.12 "$Dir\.venv"
}

Say "Instalando los componentes de Vozdoo"
& $uv pip install --quiet --python $py -r "$Dir\requirements.txt"
if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar los componentes." }
Info "Hecho."

if (-not (Test-Path "$Dir\.env")) { Copy-Item "$Dir\.env.example" "$Dir\.env" }

# 3. IA local: Ollama + modelo + asistente --------------------------------------
Say "Preparando la IA local (Ollama)"
$ollamaExe = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
$ollamaApp = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama app.exe"
if (-not (Test-Path $ollamaExe) -and -not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Info "Descargando Ollama..."
    $setup = Join-Path $env:TEMP "OllamaSetup.exe"
    Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" -OutFile $setup -UseBasicParsing
    Info "Instalando Ollama..."
    Start-Process -FilePath $setup -ArgumentList "/VERYSILENT", "/NORESTART", "/SUPPRESSMSGBOXES" -Wait
}
if (-not (Test-Ollama)) {
    if (Test-Path $ollamaApp) {
        Start-Process -FilePath $ollamaApp
    } elseif (Test-Path $ollamaExe) {
        Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
    } elseif (Get-Command ollama -ErrorAction SilentlyContinue) {
        Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    }
}
if (Wait-Ollama) {
    Info "Descargando el modelo de IA ($Model, unos 2,5 GB; solo la primera vez)..."
    & $py "$Dir\ollama_setup.py" prepare $Model
    if ($LASTEXITCODE -ne 0) { Warn "No se pudo preparar el modelo. Vozdoo te ofrecera instalarlo al usarlo." }
} else {
    Warn "Ollama no ha arrancado. Vozdoo te ofrecera instalarlo la primera vez que le pidas algo."
}

# 4. Motor de voz (Whisper), para que el primer dictado sea inmediato -----------
Say "Descargando el motor de voz (solo la primera vez)"
& $py -c "import logging; logging.disable(logging.WARNING); from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8'); print('    Hecho.')"
if ($LASTEXITCODE -ne 0) { Warn "Se descargara al abrir Vozdoo." }

# 5. Accesos directos -----------------------------------------------------------
Say "Creando el acceso directo"
$pyw = Join-Path $Dir ".venv\Scripts\pythonw.exe"
$shell = New-Object -ComObject WScript.Shell
function New-VozdooShortcut($path) {
    $lnk = $shell.CreateShortcut($path)
    $lnk.TargetPath = $pyw
    $lnk.Arguments = "`"$Dir\vozdoo_core.py`""
    $lnk.WorkingDirectory = $Dir
    $lnk.IconLocation = "$Dir\assets\icon\vozdoo.ico"
    $lnk.Description = "Dictado por voz y asistente de textos con IA local"
    $lnk.Save()
}
New-VozdooShortcut (Join-Path ([Environment]::GetFolderPath("Desktop")) "Vozdoo.lnk")
New-VozdooShortcut (Join-Path ([Environment]::GetFolderPath("Programs")) "Vozdoo.lnk")
Info "Creado Vozdoo en el escritorio y en el menu Inicio."
if (Ask-Yes "Quieres que Vozdoo se abra solo al encender el ordenador?") {
    New-VozdooShortcut (Join-Path ([Environment]::GetFolderPath("Startup")) "Vozdoo.lnk")
}

# 6. Arrancar -------------------------------------------------------------------
Say "Listo! Abriendo Vozdoo..."
Start-Process -FilePath $pyw -ArgumentList "`"$Dir\vozdoo_core.py`"" -WorkingDirectory $Dir

Write-Host @"

    Veras una bola brillante en una esquina de la pantalla. Asi se usa:

    DICTAR       Manten pulsado Ctrl + Win, habla y suelta.
                 El texto se escribe donde tengas el cursor.

    ASISTENTE    Manten pulsado Alt + Win y pide lo que quieras:
                   "Optimiza prompt profesional: quiero un plan de ventas..."
                   "Pasa esto a texto legal"
                   "Hazlo mas persuasivo"
                 Si no dices el texto, usa lo ultimo que dictaste o copiaste.

    MAS OPCIONES Boton derecho sobre la bola.

    Ya puedes cerrar esta ventana.

"@
