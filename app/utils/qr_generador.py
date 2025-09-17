# generar_qr.py
import qrcode
import os

# 🔗 Pega aquí la URL de ngrok (ajústala cada vez que cambie)
NGROK_URL = "https://3eecd5780161.ngrok-free.app".rstrip("/")

# 📂 Carpeta destino para guardar los QR
OUTPUT_DIR = "/Users/cesardaniel/Desktop/GRAY_PROJECT/QR_generade"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Lista de puntos
puntos = ["punto1", "punto2", "punto3", "punto4"]

# Generar cada QR
for punto in puntos:
    url = f"{NGROK_URL}/scan/{punto}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    filename = os.path.join(OUTPUT_DIR, f"QRLogix_{punto}.png")
    img.save(filename)

    print(f"✅ QR generado: {filename} → {url}")