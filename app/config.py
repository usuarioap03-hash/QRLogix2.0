# app/config.py

import os
import pytz

# ⚙️ Configuración general para la aplicación en Render

# URL de conexión a la base de datos (Render la inyecta como variable de entorno)
DATABASE_URL = os.getenv("DATABASE_URL")

# Duración de las sesiones en minutos (por defecto 60 si no está configurada)
SESSION_DURATION_MINUTES = int(os.getenv("SESSION_DURATION_MINUTES", 900))

# Nombre de la aplicación
APP_NAME = os.getenv("APP_NAME", "QRLogix")

# Modo debug
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# 🌎 Configuración de zona horaria
TIMEZONE = os.getenv("TIMEZONE", "America/Panama")
PANAMA_TZ = pytz.timezone(TIMEZONE)