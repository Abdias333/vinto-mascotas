"""Casos de uso. Orquestan el dominio a través de puertos."""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timedelta
from typing import Optional

from mascotas.application.ports import (
    IAvistamientoRepository,
    IEstrategiaDistancia,
    INotificacionRepository,
    IPasswordHasher,
    IPdfGenerator,
    IReporteRepository,
    IUsuarioRepository,
)
from mascotas.domain.entities import (
    AvistamientoAnonimo,
    CambioEstado,
    Coordenadas,
    EstadoReporte,
    Notificacion,
    ReporteMascota,
    Rol,
    Usuario,
)
from mascotas.domain.errors import (
    CredencialesInvalidas,
    NoEncontrado,
    PermisoDenegado,
    ValidacionError,
)
from mascotas.domain.factory import ReporteFactory

ESTADOS_BUSCABLES = (EstadoReporte.ACTIVO, EstadoReporte.COINCIDENCIA_DETECTADA)


# ----------------------------------------------------------------- matching
class MatchingService:
    """Solo decide qué reportes/avistamientos están cerca (SRP)."""

    def __init__(self, estrategia: IEstrategiaDistancia):
        self.estrategia = estrategia

    @staticmethod
    def _especie_compatible(a: str, b: str) -> bool:
        return "Desconocida" in (a, b) or a == b

    def reportes_cercanos(
        self, ubicacion: Coordenadas, especie: str, reportes: list[ReporteMascota]
    ) -> list[tuple[ReporteMascota, float]]:
        out = []
        for r in reportes:
            if r.estado not in ESTADOS_BUSCABLES:
                continue
            if not self._especie_compatible(especie, r.mascota.especie):
                continue
            d = self.estrategia.distancia_km(r.ubicacion, ubicacion)
            if d <= r.radio_km:
                out.append((r, d))
        return sorted(out, key=lambda t: t[1])

    def avistamientos_cercanos(
        self, reporte: ReporteMascota, avistamientos: list[AvistamientoAnonimo]
    ) -> list[tuple[AvistamientoAnonimo, float]]:
        out = []
        for a in avistamientos:
            if not self._especie_compatible(a.especie, reporte.mascota.especie):
                continue
            d = self.estrategia.distancia_km(reporte.ubicacion, a.ubicacion)
            if d <= reporte.radio_km:
                out.append((a, d))
        return sorted(out, key=lambda t: t[1])


# ----------------------------------------------------------------- reportes
class ReporteService:
    def __init__(
        self,
        reportes: IReporteRepository,
        avistamientos: IAvistamientoRepository,
        notificaciones: INotificacionRepository,
        matching: MatchingService,
        dias_relevantes: int = 7,
    ):
        self.reportes = reportes
        self.avistamientos = avistamientos
        self.notificaciones = notificaciones
        self.matching = matching
        self.dias_relevantes = dias_relevantes

    # -- creación
    def publicar_reporte(self, datos: dict) -> ReporteMascota:
        reporte = self.reportes.add(ReporteFactory.crear("MASCOTA_PERDIDA", datos))
        desde = datetime.now() - timedelta(days=self.dias_relevantes)
        recientes = self.avistamientos.listar(desde=desde)
        for av, dist in self.matching.avistamientos_cercanos(reporte, recientes):
            self._aplicar_coincidencia(reporte, av, dist)
        return reporte

    def registrar_avistamiento(self, datos: dict) -> tuple[AvistamientoAnonimo, int]:
        av = self.avistamientos.add(ReporteFactory.crear("AVISTAMIENTO", datos))
        activos = self.reportes.listar(estados=list(ESTADOS_BUSCABLES))
        cercanos = self.matching.reportes_cercanos(av.ubicacion, av.especie, activos)
        for reporte, dist in cercanos:
            self._aplicar_coincidencia(reporte, av, dist)
        return av, len(cercanos)

    def _aplicar_coincidencia(self, reporte, av: AvistamientoAnonimo, dist: float) -> None:
        anterior = reporte.estado
        reporte.registrar_coincidencia()
        self.reportes.actualizar(reporte)
        if anterior != reporte.estado:
            self.reportes.registrar_cambio(
                CambioEstado(reporte.id, anterior.value, reporte.estado.value, "sistema")
            )
        self.notificaciones.add(
            Notificacion(
                usuario_id=reporte.dueno_id,
                reporte_id=reporte.id,
                mensaje=(
                    f"Posible avistamiento de {reporte.mascota.nombre} a "
                    f"{dist:.2f} km de donde se perdió (zona {av.zona}, código {av.codigo})."
                ),
                distancia_km=dist,
                lat=av.ubicacion.lat,
                lon=av.ubicacion.lon,
            )
        )

    # -- gestión de estado
    def _obtener(self, reporte_id: int) -> ReporteMascota:
        r = self.reportes.get(reporte_id)
        if r is None:
            raise NoEncontrado("El reporte no existe")
        return r

    def cambiar_estado(
        self, reporte_id: int, nuevo: EstadoReporte, actor_id: int, actor_rol: Rol
    ) -> ReporteMascota:
        reporte = self._obtener(reporte_id)
        if actor_rol != Rol.ADMIN and reporte.dueno_id != actor_id:
            raise PermisoDenegado("Solo el dueño o un administrador puede cambiar el estado")
        anterior = reporte.estado
        reporte.cambiar_estado(nuevo)
        self.reportes.actualizar(reporte)
        self.reportes.registrar_cambio(
            CambioEstado(reporte_id, anterior.value, nuevo.value, f"{actor_rol.value}:{actor_id}")
        )
        return reporte

    def asignar_responsable(self, reporte_id: int, responsable: str, actor_rol: Rol) -> None:
        if actor_rol != Rol.ADMIN:
            raise PermisoDenegado("Solo un administrador puede asignar responsables")
        responsable = (responsable or "").strip()
        if len(responsable) > 80:
            raise ValidacionError("El nombre del responsable es demasiado largo")
        reporte = self._obtener(reporte_id)
        reporte.responsable = responsable or None
        self.reportes.actualizar(reporte)

    # -- consultas
    def buscar(self, filtros: Optional[dict] = None, estados=None) -> list[ReporteMascota]:
        return self.reportes.listar(filtros=filtros, estados=estados)

    def de_dueno(self, dueno_id: int) -> list[ReporteMascota]:
        return self.reportes.listar(dueno_id=dueno_id)

    def historial(self, reporte_id: int) -> list[CambioEstado]:
        return self.reportes.historial(reporte_id)

    def avistamientos_recientes(self, dias: int = 30) -> list[AvistamientoAnonimo]:
        return self.avistamientos.listar(desde=datetime.now() - timedelta(days=dias))


# ----------------------------------------------------------------- afiches
class AficheService:
    def __init__(self, reportes: IReporteRepository, usuarios: IUsuarioRepository, pdf: IPdfGenerator):
        self.reportes, self.usuarios, self.pdf = reportes, usuarios, pdf

    def generar(self, reporte_id: int) -> bytes:
        reporte = self.reportes.get(reporte_id)
        if reporte is None:
            raise NoEncontrado("El reporte no existe")
        dueno = self.usuarios.get(reporte.dueno_id)
        nombre = dueno.nombre if dueno else "el dueño"
        telefono = dueno.telefono if dueno else ""
        return self.pdf.generar_afiche(reporte, nombre, telefono)


# ----------------------------------------------------------- notificaciones
class NotificacionService:
    def __init__(self, repo: INotificacionRepository):
        self.repo = repo

    def bandeja(self, usuario_id: int) -> list[Notificacion]:
        return self.repo.de_usuario(usuario_id)

    def no_leidas(self, usuario_id: int) -> int:
        return self.repo.no_leidas(usuario_id)

    def marcar_leidas(self, usuario_id: int) -> None:
        self.repo.marcar_leidas(usuario_id)


# ------------------------------------------------------------- estadísticas
class EstadisticasService:
    def __init__(self, reportes: IReporteRepository, avistamientos: IAvistamientoRepository):
        self.reportes, self.avistamientos = reportes, avistamientos

    def resumen(self) -> dict:
        reportes = self.reportes.listar()
        total = len(reportes)
        por_estado = Counter(r.estado for r in reportes)
        rescatados = por_estado[EstadoReporte.RESCATADO]
        tiempos = [
            (r.primera_coincidencia_en - r.creado_en).total_seconds() / 3600
            for r in reportes
            if r.primera_coincidencia_en
        ]
        zonas = Counter(r.zona for r in reportes).most_common(5)
        return {
            "total": total,
            "activos": por_estado[EstadoReporte.ACTIVO] + por_estado[EstadoReporte.COINCIDENCIA_DETECTADA],
            "rescatados": rescatados,
            "archivados": por_estado[EstadoReporte.ARCHIVADO],
            "tasa_recuperacion": round(rescatados / total * 100, 1) if total else 0.0,
            "horas_primera_coincidencia": round(sum(tiempos) / len(tiempos), 2) if tiempos else None,
            "zonas_criticas": zonas,
            "avistamientos": len(self.avistamientos.listar()),
        }


# ---------------------------------------------------------------- usuarios
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_TELEFONO = re.compile(r"^\+?[\d\s-]{7,20}$")


class AuthService:
    def __init__(self, usuarios: IUsuarioRepository, hasher: IPasswordHasher):
        self.usuarios, self.hasher = usuarios, hasher

    def registrar(self, nombre: str, email: str, telefono: str, clave: str, rol: Rol = Rol.DUENO) -> Usuario:
        nombre, email, telefono = (nombre or "").strip(), (email or "").strip().lower(), (telefono or "").strip()
        if len(nombre) < 2:
            raise ValidacionError("Ingresa tu nombre")
        if not _EMAIL.match(email):
            raise ValidacionError("El correo no es válido")
        if not _TELEFONO.match(telefono):
            raise ValidacionError("El teléfono no es válido (mínimo 7 dígitos)")
        if len(clave or "") < 8:
            raise ValidacionError("La contraseña debe tener al menos 8 caracteres")
        if self.usuarios.por_email(email):
            raise ValidacionError("Ya existe una cuenta con ese correo")
        return self.usuarios.add(Usuario(nombre, email, telefono, self.hasher.hashear(clave), rol))

    def login(self, email: str, clave: str) -> Usuario:
        u = self.usuarios.por_email((email or "").strip().lower())
        if u is None or not self.hasher.verificar(clave or "", u.password_hash):
            raise CredencialesInvalidas("Correo o contraseña incorrectos")
        return u

    def asegurar_admin(self, nombre: str, email: str, clave: str) -> None:
        if self.usuarios.por_email(email.lower()) is None:
            self.registrar(nombre, email, "00000000", clave, Rol.ADMIN)
