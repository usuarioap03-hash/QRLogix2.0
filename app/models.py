# app/models.py
# Tablas de SQLAlchemy para QRLogix

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime, timedelta
from app.config import SESSION_DURATION_MINUTES

class Camion(Base):
    __tablename__ = "camiones"
    id = Column(Integer, primary_key=True, index=True)
    placa = Column(String(20), unique=True, index=True, nullable=False)
    dispositivo_id = Column(String, nullable=True)  # opcional: guarda IP o cookie
    sesiones = relationship("Sesion", back_populates="camion", cascade="all, delete-orphan")

class Sesion(Base):
    __tablename__ = "sesiones"
    id = Column(Integer, primary_key=True, index=True)
    camion_id = Column(Integer, ForeignKey("camiones.id", ondelete="CASCADE"))
    inicio = Column(DateTime, default=datetime.utcnow)
    fin = Column(
        DateTime,
        default=lambda: datetime.utcnow() + timedelta(minutes=SESSION_DURATION_MINUTES)
    )
    camion = relationship("Camion", back_populates="sesiones")
    escaneos = relationship("Escaneo", back_populates="sesion", cascade="all, delete-orphan")

class Escaneo(Base):
    __tablename__ = "escaneos"
    id = Column(Integer, primary_key=True, index=True)
    sesion_id = Column(Integer, ForeignKey("sesiones.id", ondelete="CASCADE"))
    punto = Column(String, nullable=False)
    fecha_hora = Column(DateTime, default=datetime.utcnow)
    sesion = relationship("Sesion", back_populates="escaneos")