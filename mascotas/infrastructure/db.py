"""Modelos SQLAlchemy y conexión (adaptador de persistencia)."""
from __future__ import annotations

import time
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class UsuarioModel(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    telefono: Mapped[str] = mapped_column(String(30))
    password_hash: Mapped[str] = mapped_column(String(200))
    rol: Mapped[str] = mapped_column(String(20), default="DUENO")
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class ReporteModel(Base):
    __tablename__ = "reportes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dueno_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(60))
    especie: Mapped[str] = mapped_column(String(20), index=True)
    raza: Mapped[str] = mapped_column(String(60), default="")
    color: Mapped[str] = mapped_column(String(60), default="")
    descripcion: Mapped[str] = mapped_column(Text, default="")
    foto: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    zona: Mapped[str] = mapped_column(String(80), index=True)
    fecha_perdida: Mapped[datetime] = mapped_column(DateTime)
    radio_km: Mapped[float] = mapped_column(Float)
    estado: Mapped[str] = mapped_column(String(30), index=True)
    responsable: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    primera_coincidencia_en: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AvistamientoModel(Base):
    __tablename__ = "avistamientos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(12), unique=True)
    especie: Mapped[str] = mapped_column(String(20))
    descripcion: Mapped[str] = mapped_column(Text, default="")
    foto: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    zona: Mapped[str] = mapped_column(String(80))
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)


class NotificacionModel(Base):
    __tablename__ = "notificaciones"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    reporte_id: Mapped[int] = mapped_column(ForeignKey("reportes.id"))
    mensaje: Mapped[str] = mapped_column(Text)
    distancia_km: Mapped[float] = mapped_column(Float, default=0.0)
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    leida: Mapped[bool] = mapped_column(Boolean, default=False)
    creada_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class CambioEstadoModel(Base):
    """Auditoría de cada cambio de estado."""

    __tablename__ = "cambios_estado"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reporte_id: Mapped[int] = mapped_column(ForeignKey("reportes.id"), index=True)
    anterior: Mapped[str] = mapped_column(String(30))
    nuevo: Mapped[str] = mapped_column(String(30))
    por: Mapped[str] = mapped_column(String(50))
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


def crear_motor(url):
    return create_engine(url, pool_pre_ping=True)


def iniciar_bd(engine, intentos: int = 20, espera: float = 2.0) -> None:
    """Crea las tablas; reintenta mientras PostgreSQL termina de arrancar."""
    for intento in range(1, intentos + 1):
        try:
            Base.metadata.create_all(engine)
            return
        except OperationalError as exc:
            if intento == intentos:
                raise
            print(f"[BD] No disponible aún ({intento}/{intentos}): {exc.orig}")
            time.sleep(espera)


def crear_sesiones(engine) -> sessionmaker:
    return sessionmaker(engine, expire_on_commit=False)
