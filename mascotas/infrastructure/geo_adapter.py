"""Patrón Adapter: traduce la API externa de Nominatim (OpenStreetMap)
a la interfaz IGeoService que espera la aplicación."""
from __future__ import annotations

from typing import Optional

import httpx

from mascotas import config
from mascotas.application.ports import IGeoService
from mascotas.domain.entities import Coordenadas


class NominatimClient:
    """API externa: devuelve JSON crudo."""

    URL = "https://nominatim.openstreetmap.org/search"

    def buscar(self, consulta: str) -> list[dict]:
        resp = httpx.get(
            self.URL,
            params={"q": consulta, "format": "json", "limit": 1, "countrycodes": "bo"},
            headers={"User-Agent": config.GEOCODER_USER_AGENT},
            timeout=6.0,
        )
        resp.raise_for_status()
        return resp.json()


class NominatimGeoAdapter(IGeoService):
    def __init__(self, cliente: Optional[NominatimClient] = None):
        self.cliente = cliente or NominatimClient()

    def geocodificar(self, direccion: str) -> Optional[Coordenadas]:
        direccion = (direccion or "").strip()
        if not direccion:
            return None
        try:
            datos = self.cliente.buscar(f"{direccion}, Vinto, Cochabamba, Bolivia")
            if not datos:
                return None
            return Coordenadas(float(datos[0]["lat"]), float(datos[0]["lon"]))
        except Exception:
            return None
