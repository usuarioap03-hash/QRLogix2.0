# app/utils/timezone.py
from datetime import datetime
import pytz

# Definir la zona horaria de Panamá
PANAMA_TZ = pytz.timezone("America/Panama")

def now_panama():
    """Devuelve la hora actual en la zona horaria de Panamá"""
    return datetime.now(PANAMA_TZ)