"""Lista los micrófonos disponibles para rellenar DICTADO_MIC_DEVICE en .env."""

import sounddevice as sd

if __name__ == "__main__":
    print("Dispositivos de entrada de audio disponibles:\n")
    for idx, dev in enumerate(sd.query_devices()):
        if dev.get("max_input_channels", 0) > 0:
            marker = " (por defecto)" if idx == sd.default.device[0] else ""
            print(f"  [{idx}] {dev['name']}{marker}")
    print("\nCopia el número entre [] en DICTADO_MIC_DEVICE si el micro por defecto no es el correcto.")
