# app/config.py

import os
import pytz

# ⚙️ Configuración general para la aplicación en Render

# URL de conexión a la base de datos (Render la inyecta como variable de entorno)
DATABASE_URL = os.getenv("DATABASE_URL")

# Duración de las sesiones en minutos (por defecto 15 horas si no está configurada)
SESSION_DURATION_MINUTES = int(os.getenv("SESSION_DURATION_MINUTES", 900))

# Nombre de la aplicación
APP_NAME = os.getenv("APP_NAME", "QRLogix")

# Modo debug
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# 🌎 Configuración de zona horaria
TIMEZONE = os.getenv("TIMEZONE", "America/Panama")
PANAMA_TZ = pytz.timezone(TIMEZONE)

# 🛡️ Configuración de seguridad de acceso para quienes no esten dentro de planta.
# Se modifica en render.com según necesidad.
VALIDAR_GEOZONA = os.getenv("VALIDAR_GEOZONA", "true").lower() == "true"