# tablas de SQLAlchemy

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime, timedelta
from app.config import SESSION_DURATION_MINUTES  # ✅ se importa la config

class Camion(Base):
    __tablename__ = "camiones"
    id = Column(Integer, primary_key=True, index=True)
    placa = Column(String(20), unique=True, index=True, nullable=False)
    dispositivo_id = Column(String, nullable=True)
    sesiones = relationship("Sesion", back_populates="camion")

class Sesion(Base):
    __tablename__ = "sesiones"
    id = Column(Integer, primary_key=True, index=True)
    camion_id = Column(Integer, ForeignKey("camiones.id"))
    inicio = Column(DateTime, default=datetime.utcnow)
    # ✅  usamos minutos desde config.py
    fin = Column(
        DateTime,
        default=lambda: datetime.utcnow() + timedelta(minutes=SESSION_DURATION_MINUTES)
    )
    camion = relationship("Camion", back_populates="sesiones")

class Escaneo(Base):
    __tablename__ = "escaneos"
    id = Column(Integer, primary_key=True, index=True)
    sesion_id = Column(Integer, ForeignKey("sesiones.id"))
    punto = Column(String)
    fecha_hora = Column(DateTime, default=datetime.utcnow)
    sesion = relationship("Sesion")