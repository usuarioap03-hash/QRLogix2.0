# app/crud.py
################################################

from sqlalchemy.orm import Session
from datetime import timedelta
from . import models
from app.config import SESSION_DURATION_MINUTES
from app.utils.timezone import ahora_panama

################################################
# -------------------- CAMIONES --------------------
################################################
def get_camion_by_placa(db: Session, placa: str):
    return db.query(models.Camion).filter(models.Camion.placa == placa).first()

def create_camion(db: Session, placa: str, device_cookie: str = None):
    camion = models.Camion(placa=placa, device_cookie=device_cookie)
    db.add(camion)
    db.commit()
    db.refresh(camion)
    return camion

################################################
# -------------------- SESIONES --------------------
################################################
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

def get_sesion_activa_por_cookie(db: Session, device_cookie: str):
    """
    Obtiene la sesión activa para un dispositivo identificado por cookie.
    """
    ahora = ahora_panama()
    return (
        db.query(models.Sesion)
        .join(models.Camion)
        .filter(
            models.Camion.device_cookie == device_cookie,
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

################################################
# -------------------- ESCANEOS --------------------
################################################
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

################################################
# ------------------ GESTIÓN DE SESIONES ------------------
################################################
# Cierra la sesión marcando 'fin' como la hora actual de Panamá.
def cerrar_sesion(db: Session, sesion_id: int):
    sesion = db.query(models.Sesion).filter(models.Sesion.id == sesion_id).first()
    if sesion is None:
        return None
    ahora = ahora_panama()
    sesion.fin = ahora
    db.commit()
    db.refresh(sesion)
    return sesion


# Verifica si la sesión ya registró el último punto y debe cerrarse.
def sesion_finalizo_punto(db: Session, sesion_id: int, ultimo_punto: str):
    escaneo = (
        db.query(models.Escaneo)
        .filter(
            models.Escaneo.sesion_id == sesion_id,
            models.Escaneo.punto == ultimo_punto,
        )
        .first()
    )
    return escaneo is not None