"""Patrón Factory: crea y valida reportes según su tipo."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable

from mascotas.domain.entities import (
    AvistamientoAnonimo,
    Coordenadas,
    Mascota,
    ReporteMascota,
)
from mascotas.domain.errors import ValidacionError

ESPECIES = ("Perro", "Gato", "Otro")
ESPECIES_AVISTAMIENTO = ESPECIES + ("Desconocida",)


def _texto(datos: dict, clave: str, etiqueta: str, obligatorio=False, maximo=300) -> str:
    valor = str(datos.get(clave) or "").strip()
    if obligatorio and not valor:
        raise ValidacionError(f"El campo «{etiqueta}» es obligatorio")
    if len(valor) > maximo:
        raise ValidacionError(f"«{etiqueta}» no puede superar {maximo} caracteres")
    return valor


def _coordenadas(datos: dict) -> Coordenadas:
    try:
        return Coordenadas(float(datos["lat"]), float(datos["lon"]))
    except (KeyError, TypeError, ValueError):
        raise ValidacionError("Debes marcar la ubicación en el mapa") from None


def _fecha(datos: dict) -> datetime:
    valor = datos.get("fecha")
    if not valor:
        return datetime.now()
    if isinstance(valor, str):
        try:
            valor = datetime.fromisoformat(valor)
        except ValueError:
            raise ValidacionError("La fecha no tiene un formato válido") from None
    if valor > datetime.now() + timedelta(minutes=5):
        raise ValidacionError("La fecha no puede estar en el futuro")
    return valor


class ReporteFactory:
    _creadores: dict[str, Callable[[dict], object]] = {}

    @classmethod
    def registrar(cls, tipo: str):
        def decorador(fn):
            cls._creadores[tipo] = fn
            return fn

        return decorador

    @classmethod
    def crear(cls, tipo: str, datos: dict):
        try:
            creador = cls._creadores[tipo.upper()]
        except KeyError:
            raise ValidacionError(f"Tipo de reporte desconocido: {tipo}") from None
        return creador(datos)


@ReporteFactory.registrar("MASCOTA_PERDIDA")
def _crear_mascota_perdida(datos: dict) -> ReporteMascota:
    especie = _texto(datos, "especie", "Especie", obligatorio=True)
    if especie not in ESPECIES:
        raise ValidacionError("Especie no válida")
    try:
        radio = float(datos.get("radio_km"))
    except (TypeError, ValueError):
        raise ValidacionError("Indica un radio de alerta válido") from None
    if not (0.1 <= radio <= 20):
        raise ValidacionError("El radio de alerta debe estar entre 0.1 y 20 km")
    if not datos.get("dueno_id"):
        raise ValidacionError("Se requiere un dueño autenticado")
    mascota = Mascota(
        nombre=_texto(datos, "nombre", "Nombre", obligatorio=True, maximo=60),
        especie=especie,
        raza=_texto(datos, "raza", "Raza", maximo=60),
        color=_texto(datos, "color", "Color", maximo=60),
        descripcion=_texto(datos, "descripcion", "Características", maximo=600),
        foto=datos.get("foto") or None,
    )
    return ReporteMascota(
        dueno_id=int(datos["dueno_id"]),
        mascota=mascota,
        ubicacion=_coordenadas(datos),
        zona=_texto(datos, "zona", "Zona", obligatorio=True, maximo=80),
        fecha_perdida=_fecha(datos),
        radio_km=radio,
    )


@ReporteFactory.registrar("AVISTAMIENTO")
def _crear_avistamiento(datos: dict) -> AvistamientoAnonimo:
    especie = _texto(datos, "especie", "Especie", obligatorio=True)
    if especie not in ESPECIES_AVISTAMIENTO:
        raise ValidacionError("Especie no válida")
    return AvistamientoAnonimo(
        ubicacion=_coordenadas(datos),
        zona=_texto(datos, "zona", "Zona", obligatorio=True, maximo=80),
        especie=especie,
        descripcion=_texto(datos, "descripcion", "Descripción", maximo=400),
        foto=datos.get("foto") or None,
    )
