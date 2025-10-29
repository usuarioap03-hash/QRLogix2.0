# app/utils/timezone.py
from datetime import datetime
import pytz
from app.config import PANAMA_TZ as CONFIG_PANAMA_TZ

PANAMA_TZ = CONFIG_PANAMA_TZ

def ahora_panama() -> datetime:
    """Devuelve la hora actual en Panamá"""
    return datetime.now(PANAMA_TZ)

def convertir_a_panama(dt: datetime) -> datetime:
    """Convierte un datetime a la hora de Panamá"""
    if dt is None:
        return None
    if dt.tzinfo is None:  # si es naive, asumimos UTC
        dt = dt.replace(tzinfo=pytz.UTC)
    return dt.astimezone(PANAMA_TZ)

def formatear_hora_panama(dt: datetime) -> str:
    """Devuelve la hora en formato de Panamá con notación 12h am/pm."""
    if dt is None:
        return ""
    dt_local = convertir_a_panama(dt)
    return dt_local.strftime("%I:%M %p").lstrip("0").lower()
