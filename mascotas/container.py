"""Raíz de composición: aquí se conectan puertos con adaptadores."""
from mascotas import config
from mascotas.application.distance import HaversineStrategy
from mascotas.application.services import (
    AficheService,
    AuthService,
    EstadisticasService,
    MatchingService,
    NotificacionService,
    ReporteService,
)
from mascotas.infrastructure.db import crear_motor, crear_sesiones, iniciar_bd
from mascotas.infrastructure.geo_adapter import NominatimGeoAdapter
from mascotas.infrastructure.pdf_adapter import ReportLabAficheAdapter
from mascotas.infrastructure.repositories import (
    SqlAvistamientoRepository,
    SqlNotificacionRepository,
    SqlReporteRepository,
    SqlUsuarioRepository,
)
from mascotas.infrastructure.security import BcryptHasher
from mascotas.infrastructure.storage import FotoStorage


class Contenedor:
    def __init__(self):
        motor = crear_motor(config.DATABASE_URL)
        iniciar_bd(motor)
        sf = crear_sesiones(motor)

        usuarios = SqlUsuarioRepository(sf)
        reportes = SqlReporteRepository(sf)
        avistamientos = SqlAvistamientoRepository(sf)
        notifs = SqlNotificacionRepository(sf)

        self.geo = NominatimGeoAdapter()
        self.storage = FotoStorage(config.MEDIA_DIR)
        self.auth = AuthService(usuarios, BcryptHasher())
        self.reportes = ReporteService(
            reportes, avistamientos, notifs, MatchingService(HaversineStrategy())
        )
        self.afiches = AficheService(reportes, usuarios, ReportLabAficheAdapter(config.MEDIA_DIR))
        self.notificaciones = NotificacionService(notifs)
        self.estadisticas = EstadisticasService(reportes, avistamientos)

        self.auth.asegurar_admin(config.ADMIN_NOMBRE, config.ADMIN_EMAIL, config.ADMIN_PASSWORD)
