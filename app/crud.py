# app/crud.py
# funciones de CRUD acceso a datos
# (Crear=POST, Leer=GET, Actualizar=PUT, Eliminar=DELETE)

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from . import models
from app.config import SESSION_DURATION_MINUTES

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
    ahora = datetime.utcnow()
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
    ahora = datetime.utcnow()
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
    inicio = datetime.utcnow()
    fin = inicio + timedelta(minutes=minutes)
    sesion = models.Sesion(camion_id=camion_id, inicio=inicio, fin=fin)
    db.add(sesion)
    db.commit()
    db.refresh(sesion)
    return sesion

# ------------------ ESCANEOS ------------------
def create_escaneo(db: Session, sesion_id: int, punto: str):
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
        return ya  # evita duplicados por refresh o recarga del QR

    escaneo = models.Escaneo(
        sesion_id=sesion_id,
        punto=punto,
        fecha_hora=datetime.utcnow(),
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
        fecha_hora=datetime.utcnow(),
    )
    db.add(alerta)
    db.commit()
    db.refresh(alerta)
    return alerta

# ------------------ SEGURIDAD: PLACAS AUTORIZADAS ------------------
def placa_autorizada_existe(db: Session, placa: str) -> bool:
    return db.query(models.PlacaAutorizada).filter_by(placa=placa).first() is not None

# ------------------ SEGURIDAD: DISPOSITIVOS AUTORIZADOS ------------------
def registrar_dispositivo_autorizado(db: Session, dispositivo_id: str, placa: str):
    disp = models.DispositivoAutorizado(dispositivo_id=dispositivo_id, placa=placa)
    db.add(disp)
    db.commit()
    db.refresh(disp)
    return disp

def dispositivo_autorizado_valido(db: Session, dispositivo_id: str, placa: str) -> bool:
    return (
        db.query(models.DispositivoAutorizado)
        .filter_by(dispositivo_id=dispositivo_id, placa=placa)
        .first()
        is not None
    )