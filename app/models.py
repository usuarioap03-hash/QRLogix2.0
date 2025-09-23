# app/models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import timedelta
from app.config import SESSION_DURATION_MINUTES
from app.utils.timezone import ahora_panama

class Camion(Base):
    __tablename__ = "camiones"
    id = Column(Integer, primary_key=True, index=True)
    placa = Column(String(20), unique=True, index=True, nullable=False)
    device_cookie = Column(String, nullable=True, unique=True)  # Identificador único por cookie
    sesiones = relationship("Sesion", back_populates="camion", cascade="all, delete-orphan")

class Sesion(Base):
    __tablename__ = "sesiones"
    id = Column(Integer, primary_key=True, index=True)
    camion_id = Column(Integer, ForeignKey("camiones.id", ondelete="CASCADE"))
    inicio = Column(DateTime(timezone=True), default=ahora_panama, nullable=False)

    @staticmethod
    def default_fin():
        return ahora_panama() + timedelta(minutes=SESSION_DURATION_MINUTES)

    fin = Column(DateTime(timezone=True), default=default_fin, nullable=False)
    cerrada = Column(Boolean, default=False)
    camion = relationship("Camion", back_populates="sesiones")
    ciclos = relationship("Ciclo", back_populates="sesion", cascade="all, delete-orphan")

class Ciclo(Base):
    __tablename__ = "ciclos"
    id = Column(Integer, primary_key=True, index=True)
    sesion_id = Column(Integer, ForeignKey("sesiones.id", ondelete="CASCADE"))
    inicio = Column(DateTime(timezone=True), default=ahora_panama, nullable=False)
    fin = Column(DateTime(timezone=True), nullable=True)
    completado = Column(Boolean, default=False)

    sesion = relationship("Sesion", back_populates="ciclos")
    escaneos = relationship("Escaneo", back_populates="ciclo", cascade="all, delete-orphan")

class Escaneo(Base):
    __tablename__ = "escaneos"
    id = Column(Integer, primary_key=True, index=True)
    ciclo_id = Column(Integer, ForeignKey("ciclos.id", ondelete="CASCADE"))
    punto = Column(String, nullable=False)
    fecha_hora = Column(DateTime(timezone=True), default=ahora_panama, nullable=False)

    ciclo = relationship("Ciclo", back_populates="escaneos")