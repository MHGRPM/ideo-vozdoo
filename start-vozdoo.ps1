$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

if (-not (Test-Path ".venv")) {
    Write-Host "==> Creando entorno virtual (.venv)..."
    python -m venv .venv
}

Write-Host "==> Activando entorno virtual..."
& ".venv\Scripts\Activate.ps1"

Write-Host "==> Instalando dependencias (la primera vez puede tardar 1-3 minutos, descarga el motor de Whisper)..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python -c "from PyQt6.QtWidgets import QApplication" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "==> Aviso: PyQt6 no arranca. No tendrás el orbe flotante ni el pulido con IA, pero el dictado normal (Ctrl+Win) sí funciona."
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "==> Creado .env con valores por defecto. Editalo si quieres cambiar la tecla o el modelo."
}

Write-Host "==> Arrancando Vozdoo (la primera vez tarda otro poco más descargando el modelo Whisper)..."
python vozdoo_core.py
