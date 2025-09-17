# app/config.py

import os

# ⚙️ Configuración general para la aplicación en Render

# URL de conexión a la base de datos (Render la inyecta como variable de entorno)
DATABASE_URL = os.getenv("DATABASE_URL")

# Duración de las sesiones en minutos (por defecto 60 si no está configurada)
SESSION_DURATION_MINUTES = int(os.getenv("SESSION_DURATION_MINUTES", 60))

# (Opcional) Configuración adicional
APP_NAME = os.getenv("APP_NAME", "QRLogix")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"