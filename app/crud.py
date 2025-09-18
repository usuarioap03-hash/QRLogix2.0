# app/crud.py
from sqlalchemy.orm import Session
from datetime import timedelta
from . import models
from app.config import SESSION_DURATION_MINUTES
from app.utils.timezone import ahora_panama

# ------------------ CAMIONES ------------------
def get_camion_by_placa(db: Session, placa: str):
    return db.query(models.Camion).filter(models.Camion.placa == placa).first()

def create_camion(db: Session, placa: str, dispositivo_id: str = None):
    camion = models.Camion(placa=placa, dispositivo_id=dispositivo_id)
    db.add(camion)
    db.commit()
    db.refresh(camion)
    return camion

# ------------------ SESIONES ------------------
def get_sesion_activa(db: Session, camion_id: int):
    ahora = ahora_panama()
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
    ahora = ahora_panama()
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
    if minutes is None:
        minutes = SESSION_DURATION_MINUTES
    inicio = ahora_panama()
    fin = inicio + timedelta(minutes=minutes)
    sesion = models.Sesion(camion_id=camion_id, inicio=inicio, fin=fin)
    db.add(sesion)
    db.commit()
    db.refresh(sesion)
    return sesion

# ------------------ ESCANEOS ------------------
def create_escaneo(db: Session, sesion_id: int, punto: str):
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
        fecha_hora=ahora_panama(),
    )
    db.add(escaneo)
    db.commit()
    db.refresh(escaneo)
    return escaneo