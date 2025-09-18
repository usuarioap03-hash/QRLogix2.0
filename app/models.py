# app/models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import timedelta
from app.config import SESSION_DURATION_MINUTES
from app.utils.timezone import ahora_panama

class Camion(Base):
    __tablename__ = "camiones"
    id = Column(Integer, primary_key=True, index=True)
    placa = Column(String(20), unique=True, index=True, nullable=False)
    dispositivo_id = Column(String, nullable=True)
    sesiones = relationship("Sesion", back_populates="camion", cascade="all, delete-orphan")

class Sesion(Base):
    __tablename__ = "sesiones"
    id = Column(Integer, primary_key=True, index=True)
    camion_id = Column(Integer, ForeignKey("camiones.id", ondelete="CASCADE"))
    inicio = Column(DateTime, default=ahora_panama)
    fin = Column(DateTime, default=lambda: ahora_panama() + timedelta(minutes=SESSION_DURATION_MINUTES))
    camion = relationship("Camion", back_populates="sesiones")
    escaneos = relationship("Escaneo", back_populates="sesion", cascade="all, delete-orphan")

class Escaneo(Base):
    __tablename__ = "escaneos"
    id = Column(Integer, primary_key=True, index=True)
    sesion_id = Column(Integer, ForeignKey("sesiones.id", ondelete="CASCADE"))
    punto = Column(String, nullable=False)
    fecha_hora = Column(DateTime, default=ahora_panama)
    sesion = relationship("Sesion", back_populates="escaneos")

class Alerta(Base):
    __tablename__ = "alertas"
    id = Column(Integer, primary_key=True, index=True)
    sesion_id = Column(Integer, ForeignKey("sesiones.id", ondelete="CASCADE"))
    punto_saltado = Column(String, nullable=False)
    fecha_hora = Column(DateTime, default=ahora_panama)