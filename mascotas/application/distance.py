"""Estrategias de distancia (OCP: se agregan nuevas sin tocar MatchingService)."""
from __future__ import annotations

import math

from mascotas.application.ports import IEstrategiaDistancia
from mascotas.domain.entities import Coordenadas

RADIO_TIERRA_KM = 6371.0088


class HaversineStrategy(IEstrategiaDistancia):
    def distancia_km(self, a: Coordenadas, b: Coordenadas) -> float:
        p1, p2 = math.radians(a.lat), math.radians(b.lat)
        dphi = p2 - p1
        dlambda = math.radians(b.lon - a.lon)
        h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
        return 2 * RADIO_TIERRA_KM * math.asin(math.sqrt(h))


class ManhattanStrategy(IEstrategiaDistancia):
    """Aproximación de distancia por manzanas (norte-sur + este-oeste)."""

    def distancia_km(self, a: Coordenadas, b: Coordenadas) -> float:
        lat_media = math.radians((a.lat + b.lat) / 2)
        km_lat = abs(a.lat - b.lat) * 111.32
        km_lon = abs(a.lon - b.lon) * 111.32 * math.cos(lat_media)
        return km_lat + km_lon
