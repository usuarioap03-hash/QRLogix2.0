# horas de panama
from datetime import datetime
from zoneinfo import ZoneInfo

def ahora_panama() -> datetime:
    """Devuelve la hora actual en la zona horaria de Panamá"""
    return datetime.now(ZoneInfo("America/Panama"))

def convertir_a_panama(dt: datetime) -> datetime:
    """Convierte un datetime UTC a hora Panamá"""
    if dt is None:
        return None
    return dt.astimezone(ZoneInfo("America/Panama"))