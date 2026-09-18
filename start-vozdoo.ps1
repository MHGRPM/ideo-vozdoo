$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

if (-not (Test-Path ".venv")) {
    Write-Host "Creando entorno virtual..."
    python -m venv .venv
}

& ".venv\Scripts\Activate.ps1"

python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Creado .env con valores por defecto. Editalo si quieres cambiar la tecla o el modelo."
}

python vozdoo_core.py
