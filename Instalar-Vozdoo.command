#!/usr/bin/env bash
# Doble clic aquí (en Mac) para instalar o actualizar Vozdoo.
cd "$(dirname "$0")"
bash ./install.sh
echo
read -r -p "Pulsa Enter para cerrar esta ventana" _
