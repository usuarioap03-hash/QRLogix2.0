# app/utils/timezone.py
import pytz
from datetime import datetime

PANAMA_TZ = pytz.timezone("America/Panama")

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