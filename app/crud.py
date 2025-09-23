# app/crud.py
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
    sesion = models.Sesion(camion_id=camion_id, placa=placa)
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
    ciclo = models.Ciclo(sesion_id=sesion_id)
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
def create_escaneo(db: Session, ciclo_id: int, punto: str):
    escaneo = models.Escaneo(ciclo_id=ciclo_id, punto=punto)
    db.add(escaneo)
    db.commit()
    db.refresh(escaneo)
    return escaneo