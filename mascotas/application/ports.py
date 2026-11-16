"""Puertos (interfaces). La aplicación depende de estas abstracciones (DIP)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from mascotas.domain.entities import (
    AvistamientoAnonimo,
    CambioEstado,
    Coordenadas,
    EstadoReporte,
    Notificacion,
    ReporteMascota,
    Usuario,
)


class IReporteRepository(ABC):
    @abstractmethod
    def add(self, reporte: ReporteMascota) -> ReporteMascota: ...

    @abstractmethod
    def get(self, reporte_id: int) -> Optional[ReporteMascota]: ...

    @abstractmethod
    def actualizar(self, reporte: ReporteMascota) -> None: ...

    @abstractmethod
    def listar(
        self,
        filtros: Optional[dict] = None,
        dueno_id: Optional[int] = None,
        estados: Optional[list[EstadoReporte]] = None,
    ) -> list[ReporteMascota]: ...

    @abstractmethod
    def registrar_cambio(self, cambio: CambioEstado) -> None: ...

    @abstractmethod
    def historial(self, reporte_id: int) -> list[CambioEstado]: ...


class IAvistamientoRepository(ABC):
    @abstractmethod
    def add(self, avistamiento: AvistamientoAnonimo) -> AvistamientoAnonimo: ...

    @abstractmethod
    def listar(self, desde: Optional[datetime] = None) -> list[AvistamientoAnonimo]: ...


class IUsuarioRepository(ABC):
    @abstractmethod
    def add(self, usuario: Usuario) -> Usuario: ...

    @abstractmethod
    def por_email(self, email: str) -> Optional[Usuario]: ...

    @abstractmethod
    def get(self, usuario_id: int) -> Optional[Usuario]: ...


class INotificacionRepository(ABC):
    @abstractmethod
    def add(self, notificacion: Notificacion) -> Notificacion: ...

    @abstractmethod
    def de_usuario(self, usuario_id: int) -> list[Notificacion]: ...

    @abstractmethod
    def no_leidas(self, usuario_id: int) -> int: ...

    @abstractmethod
    def marcar_leidas(self, usuario_id: int) -> None: ...


class IGeoService(ABC):
    @abstractmethod
    def geocodificar(self, direccion: str) -> Optional[Coordenadas]: ...


class IPdfGenerator(ABC):
    @abstractmethod
    def generar_afiche(
        self, reporte: ReporteMascota, contacto_nombre: str, contacto_telefono: str
    ) -> bytes: ...


class IPasswordHasher(ABC):
    @abstractmethod
    def hashear(self, clave: str) -> str: ...

    @abstractmethod
    def verificar(self, clave: str, hash_: str) -> bool: ...


class IEstrategiaDistancia(ABC):
    @abstractmethod
    def distancia_km(self, a: Coordenadas, b: Coordenadas) -> float: ...
