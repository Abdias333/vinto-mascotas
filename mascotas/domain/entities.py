"""Entidades puras del dominio. No dependen de ningún framework."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from mascotas.domain.errors import TransicionInvalida, ValidacionError


class Rol(str, Enum):
    DUENO = "DUENO"
    ADMIN = "ADMIN"


class EstadoReporte(str, Enum):
    ACTIVO = "ACTIVO"
    COINCIDENCIA_DETECTADA = "COINCIDENCIA_DETECTADA"
    RESCATADO = "RESCATADO"
    ARCHIVADO = "ARCHIVADO"

    @property
    def etiqueta(self) -> str:
        return self.value.replace("_", " ").capitalize()

    def puede_pasar_a(self, nuevo: "EstadoReporte") -> bool:
        return nuevo in TRANSICIONES[self]


TRANSICIONES = {
    EstadoReporte.ACTIVO: {
        EstadoReporte.COINCIDENCIA_DETECTADA,
        EstadoReporte.RESCATADO,
        EstadoReporte.ARCHIVADO,
    },
    EstadoReporte.COINCIDENCIA_DETECTADA: {
        EstadoReporte.ACTIVO,
        EstadoReporte.RESCATADO,
        EstadoReporte.ARCHIVADO,
    },
    EstadoReporte.RESCATADO: {EstadoReporte.ARCHIVADO},
    EstadoReporte.ARCHIVADO: {EstadoReporte.ACTIVO},
}


@dataclass(frozen=True)
class Coordenadas:
    """Objeto de valor: un punto geográfico válido."""

    lat: float
    lon: float

    def __post_init__(self):
        if not (-90 <= self.lat <= 90 and -180 <= self.lon <= 180):
            raise ValidacionError("Las coordenadas están fuera de rango")


@dataclass
class Usuario:
    nombre: str
    email: str
    telefono: str
    password_hash: str
    rol: Rol = Rol.DUENO
    id: Optional[int] = None
    creado_en: datetime = field(default_factory=datetime.now)


@dataclass
class Mascota:
    nombre: str
    especie: str
    raza: str = ""
    color: str = ""
    descripcion: str = ""
    foto: Optional[str] = None


@dataclass
class ReporteMascota:
    dueno_id: int
    mascota: Mascota
    ubicacion: Coordenadas
    zona: str
    fecha_perdida: datetime
    radio_km: float
    estado: EstadoReporte = EstadoReporte.ACTIVO
    responsable: Optional[str] = None
    id: Optional[int] = None
    creado_en: datetime = field(default_factory=datetime.now)
    primera_coincidencia_en: Optional[datetime] = None

    def cambiar_estado(self, nuevo: EstadoReporte) -> None:
        if not self.estado.puede_pasar_a(nuevo):
            raise TransicionInvalida(
                f"No se puede pasar de {self.estado.etiqueta} a {nuevo.etiqueta}"
            )
        self.estado = nuevo

    def registrar_coincidencia(self) -> None:
        if self.primera_coincidencia_en is None:
            self.primera_coincidencia_en = datetime.now()
        if self.estado == EstadoReporte.ACTIVO:
            self.estado = EstadoReporte.COINCIDENCIA_DETECTADA


def _codigo() -> str:
    return uuid.uuid4().hex[:8].upper()


@dataclass
class AvistamientoAnonimo:
    ubicacion: Coordenadas
    zona: str
    especie: str
    descripcion: str = ""
    foto: Optional[str] = None
    fecha: datetime = field(default_factory=datetime.now)
    codigo: str = field(default_factory=_codigo)
    id: Optional[int] = None


@dataclass
class Notificacion:
    usuario_id: int
    reporte_id: int
    mensaje: str
    distancia_km: float = 0.0
    lat: Optional[float] = None
    lon: Optional[float] = None
    leida: bool = False
    id: Optional[int] = None
    creada_en: datetime = field(default_factory=datetime.now)


@dataclass
class CambioEstado:
    reporte_id: int
    anterior: str
    nuevo: str
    por: str
    fecha: datetime = field(default_factory=datetime.now)
    id: Optional[int] = None
