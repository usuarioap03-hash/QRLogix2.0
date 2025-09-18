# app/crud.py
from sqlalchemy.orm import Session
from datetime import timedelta
from . import models
from app.config import SESSION_DURATION_MINUTES
from app.utils.timezone import now_panama  # ✅ usamos hora de Panamá

# ------------------ CAMIONES ------------------
def get_camion_by_placa(db: Session, placa: str):
    """Busca un camión por su placa"""
    return db.query(models.Camion).filter(models.Camion.placa == placa).first()

def create_camion(db: Session, placa: str, dispositivo_id: str = None):
    """Crea un nuevo camión en la BD"""
    camion = models.Camion(placa=placa, dispositivo_id=dispositivo_id)
    db.add(camion)
    db.commit()
    db.refresh(camion)
    return camion

# ------------------ SESIONES ------------------
def get_sesion_activa(db: Session, camion_id: int):
    """Busca sesión activa por ID de camión"""
    ahora = now_panama()
    return (
        db.query(models.Sesion)
        .filter(
            models.Sesion.camion_id == camion_id,
            models.Sesion.inicio <= ahora,
            models.Sesion.fin >= ahora,
        )
        .first()
    )

def get_sesion_activa_por_ip(db: Session, dispositivo_id: str):
    """Busca sesión activa usando el dispositivo/IP (si guardas IP en Camion.dispositivo_id)"""
    ahora = now_panama()
    return (
        db.query(models.Sesion)
        .join(models.Camion)
        .filter(
            models.Camion.dispositivo_id == dispositivo_id,
            models.Sesion.fin > ahora,
        )
        .first()
    )

def create_sesion(db: Session, camion_id: int, minutes: int | None = None):
    """Crea nueva sesión: por defecto usa SESSION_DURATION_MINUTES del config"""
    if minutes is None:
        minutes = SESSION_DURATION_MINUTES
    inicio = now_panama()
    fin = inicio + timedelta(minutes=minutes)
    sesion = models.Sesion(camion_id=camion_id, inicio=inicio, fin=fin)
    db.add(sesion)
    db.commit()
    db.refresh(sesion)
    return sesion

# ------------------ ESCANEOS ------------------
def create_escaneo(db: Session, sesion_id: int, punto: str, estado: str = "OK"):
    """Crea un registro de escaneo si no existe ya ese punto en esta sesión (idempotente)"""
    ya = (
        db.query(models.Escaneo)
        .filter(
            models.Escaneo.sesion_id == sesion_id,
            models.Escaneo.punto == punto,
        )
        .first()
    )
    if ya:
        return ya

    escaneo = models.Escaneo(
        sesion_id=sesion_id,
        punto=punto,
        fecha_hora=now_panama() if estado == "OK" else None,
        estado=estado
    )
    db.add(escaneo)
    db.commit()
    db.refresh(escaneo)
    return escaneo

# ------------------ ALERTAS (si se reactivan en el futuro) ------------------
def create_alerta(db: Session, sesion_id: int, punto_saltado: str):
    """Crea un registro de alerta"""
    alerta = models.Alerta(
        sesion_id=sesion_id,
        punto_saltado=punto_saltado,
        fecha_hora=now_panama(),  # ✅ Panamá
    )
    db.add(alerta)
    db.commit()
    db.refresh(alerta)
    return alerta