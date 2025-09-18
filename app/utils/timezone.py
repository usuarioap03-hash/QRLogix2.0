# app/utils/timezone.py
from datetime import datetime
import pytz

# Zona horaria de Panamá
PANAMA_TZ = pytz.timezone("America/Panama")

def now_panama() -> datetime:
    """Devuelve la hora actual en la zona horaria de Panamá"""
    return datetime.now(PANAMA_TZ)