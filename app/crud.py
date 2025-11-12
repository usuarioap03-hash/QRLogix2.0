# app/crud.py
from datetime import timedelta
from sqlalchemy.orm import Session
from app import models
from app.utils.timezone import ahora_panama

# Crear camion
def create_camion(db: Session, device_cookie: str):
    camion = models.Camion(device_cookie=device_cookie)
    db.add(camion)
    db.commit()
    db.refresh(camion)
    return camion

def get_camion_by_cookie(db: Session, cookie: str):
    return db.query(models.Camion).filter(models.Camion.device_cookie == cookie).first()

# Sesiones
def create_sesion(db: Session, camion_id: int, placa: str):
    sesion = models.Sesion(
        camion_id=camion_id,
        placa=placa,
        inicio=ahora_panama(),
        fin=models.Sesion.default_fin()
    )
    db.add(sesion)
    db.commit()
    db.refresh(sesion)
    return sesion

def get_sesion_activa(db: Session, camion_id: int):
    return db.query(models.Sesion).filter(
        models.Sesion.camion_id == camion_id,
        models.Sesion.cerrada == False,
        models.Sesion.fin >= ahora_panama()
    ).order_by(models.Sesion.id.desc()).first()

# Ciclos
def create_ciclo(db: Session, sesion_id: int):
    ciclo = models.Ciclo(sesion_id=sesion_id, inicio=ahora_panama())
    db.add(ciclo)
    db.commit()
    db.refresh(ciclo)
    return ciclo

def get_ciclo_activo(db: Session, sesion_id: int):
    return db.query(models.Ciclo).filter(
        models.Ciclo.sesion_id == sesion_id,
        models.Ciclo.completado == False
    ).order_by(models.Ciclo.id.desc()).first()

# Escaneos
def create_escaneo(
    db: Session,
    ciclo_id: int,
    punto: str,
    device_cookie: str | None = None
):
    """
    Crea un escaneo para un ciclo y punto.

    - Evita duplicar el mismo punto en el mismo ciclo si ya hubo uno
      en los últimos 60 minutos.
    - El parámetro device_cookie se acepta por compatibilidad,
      pero **NO** se guarda en la tabla escaneos, porque el modelo
      Escaneo no tiene esa columna.
    """
    hace_60_min = ahora_panama() - timedelta(minutes=60)

    ultimo = (
        db.query(models.Escaneo)
        .filter(
            models.Escaneo.ciclo_id == ciclo_id,
            models.Escaneo.punto == punto
        )
        .order_by(models.Escaneo.fecha_hora.desc())
        .first()
    )

    if ultimo and ultimo.fecha_hora >= hace_60_min:
        # Ya hay un escaneo reciente de este mismo punto en este ciclo → no duplicamos
        return ultimo

    escaneo = models.Escaneo(
        ciclo_id=ciclo_id,
        punto=punto,
        fecha_hora=ahora_panama()
        # 👈 IMPORTANTE: aquí NO va device_cookie
    )
    db.add(escaneo)
    db.commit()
    db.refresh(escaneo)
    return escaneo

def get_sesion_activa_por_placa(db: Session, placa: str):
    """Obtiene la sesión activa más reciente para una placa sin importar la cookie."""
    return db.query(models.Sesion).filter(
        models.Sesion.placa == placa,
        models.Sesion.cerrada == False,
        models.Sesion.fin >= ahora_panama()
    ).order_by(models.Sesion.id.desc()).first()

def get_ultimo_escaneo_por_ciclo(db: Session, ciclo_id: int):
    """Devuelve el último escaneo registrado para un ciclo."""
    return (
        db.query(models.Escaneo)
        .filter(models.Escaneo.ciclo_id == ciclo_id)
        .order_by(models.Escaneo.fecha_hora.desc())
        .first()
    )