"""Adaptadores de persistencia: implementan los puertos con SQLAlchemy."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, select, update

from mascotas.application.ports import (
    IAvistamientoRepository,
    INotificacionRepository,
    IReporteRepository,
    IUsuarioRepository,
)
from mascotas.domain.entities import (
    AvistamientoAnonimo,
    CambioEstado,
    Coordenadas,
    EstadoReporte,
    Mascota,
    Notificacion,
    ReporteMascota,
    Rol,
    Usuario,
)
from mascotas.infrastructure.db import (
    AvistamientoModel,
    CambioEstadoModel,
    NotificacionModel,
    ReporteModel,
    UsuarioModel,
)


def _fecha_iso(valor):
    """Convierte 'AAAA-MM-DD' en datetime; devuelve None si no es una fecha válida."""
    try:
        return datetime.fromisoformat(str(valor))
    except ValueError:
        return None


class SqlUsuarioRepository(IUsuarioRepository):
    def __init__(self, sf):
        self._sf = sf

    @staticmethod
    def _dom(m: UsuarioModel) -> Usuario:
        return Usuario(m.nombre, m.email, m.telefono, m.password_hash, Rol(m.rol), m.id, m.creado_en)

    def add(self, u: Usuario) -> Usuario:
        with self._sf() as s:
            m = UsuarioModel(
                nombre=u.nombre, email=u.email, telefono=u.telefono,
                password_hash=u.password_hash, rol=u.rol.value, creado_en=u.creado_en,
            )
            s.add(m)
            s.commit()
            u.id = m.id
        return u

    def por_email(self, email: str) -> Optional[Usuario]:
        with self._sf() as s:
            m = s.scalar(select(UsuarioModel).where(UsuarioModel.email == email))
            return self._dom(m) if m else None

    def get(self, usuario_id: int) -> Optional[Usuario]:
        with self._sf() as s:
            m = s.get(UsuarioModel, usuario_id)
            return self._dom(m) if m else None


class SqlReporteRepository(IReporteRepository):
    def __init__(self, sf):
        self._sf = sf

    @staticmethod
    def _dom(m: ReporteModel) -> ReporteMascota:
        return ReporteMascota(
            id=m.id,
            dueno_id=m.dueno_id,
            mascota=Mascota(m.nombre, m.especie, m.raza, m.color, m.descripcion, m.foto),
            ubicacion=Coordenadas(m.lat, m.lon),
            zona=m.zona,
            fecha_perdida=m.fecha_perdida,
            radio_km=m.radio_km,
            estado=EstadoReporte(m.estado),
            responsable=m.responsable,
            creado_en=m.creado_en,
            primera_coincidencia_en=m.primera_coincidencia_en,
        )

    def add(self, r: ReporteMascota) -> ReporteMascota:
        with self._sf() as s:
            m = ReporteModel(
                dueno_id=r.dueno_id, nombre=r.mascota.nombre, especie=r.mascota.especie,
                raza=r.mascota.raza, color=r.mascota.color, descripcion=r.mascota.descripcion,
                foto=r.mascota.foto, lat=r.ubicacion.lat, lon=r.ubicacion.lon, zona=r.zona,
                fecha_perdida=r.fecha_perdida, radio_km=r.radio_km, estado=r.estado.value,
                responsable=r.responsable, creado_en=r.creado_en,
                primera_coincidencia_en=r.primera_coincidencia_en,
            )
            s.add(m)
            s.commit()
            r.id = m.id
        return r

    def get(self, reporte_id: int) -> Optional[ReporteMascota]:
        with self._sf() as s:
            m = s.get(ReporteModel, reporte_id)
            return self._dom(m) if m else None

    def actualizar(self, r: ReporteMascota) -> None:
        with self._sf() as s:
            s.execute(
                update(ReporteModel)
                .where(ReporteModel.id == r.id)
                .values(
                    estado=r.estado.value,
                    responsable=r.responsable,
                    primera_coincidencia_en=r.primera_coincidencia_en,
                )
            )
            s.commit()

    def listar(self, filtros=None, dueno_id=None, estados=None) -> list[ReporteMascota]:
        filtros = {k: v for k, v in (filtros or {}).items() if v}
        stmt = select(ReporteModel).order_by(ReporteModel.creado_en.desc())
        if dueno_id is not None:
            stmt = stmt.where(ReporteModel.dueno_id == dueno_id)
        if estados:
            stmt = stmt.where(ReporteModel.estado.in_([e.value for e in estados]))
        if "estado" in filtros:
            stmt = stmt.where(ReporteModel.estado == filtros["estado"])
        if "especie" in filtros:
            stmt = stmt.where(ReporteModel.especie == filtros["especie"])
        if "zona" in filtros:
            stmt = stmt.where(ReporteModel.zona == filtros["zona"])
        if "raza" in filtros:
            stmt = stmt.where(ReporteModel.raza.ilike(f"%{filtros['raza']}%"))
        if "color" in filtros:
            stmt = stmt.where(ReporteModel.color.ilike(f"%{filtros['color']}%"))
        if "desde" in filtros:
            desde = _fecha_iso(filtros["desde"])
            if desde:
                stmt = stmt.where(ReporteModel.fecha_perdida >= desde)
        if "hasta" in filtros:
            hasta = _fecha_iso(filtros["hasta"])
            if hasta:  # se suma un día para incluir todo el día "hasta"
                stmt = stmt.where(ReporteModel.fecha_perdida < hasta + timedelta(days=1))
        with self._sf() as s:
            return [self._dom(m) for m in s.scalars(stmt)]

    def registrar_cambio(self, c: CambioEstado) -> None:
        with self._sf() as s:
            s.add(CambioEstadoModel(
                reporte_id=c.reporte_id, anterior=c.anterior, nuevo=c.nuevo, por=c.por, fecha=c.fecha
            ))
            s.commit()

    def historial(self, reporte_id: int) -> list[CambioEstado]:
        stmt = (
            select(CambioEstadoModel)
            .where(CambioEstadoModel.reporte_id == reporte_id)
            .order_by(CambioEstadoModel.fecha.desc(), CambioEstadoModel.id.desc())
        )
        with self._sf() as s:
            return [
                CambioEstado(m.reporte_id, m.anterior, m.nuevo, m.por, m.fecha, m.id)
                for m in s.scalars(stmt)
            ]


class SqlAvistamientoRepository(IAvistamientoRepository):
    def __init__(self, sf):
        self._sf = sf

    @staticmethod
    def _dom(m: AvistamientoModel) -> AvistamientoAnonimo:
        return AvistamientoAnonimo(
            ubicacion=Coordenadas(m.lat, m.lon), zona=m.zona, especie=m.especie,
            descripcion=m.descripcion, foto=m.foto, fecha=m.fecha, codigo=m.codigo, id=m.id,
        )

    def add(self, a: AvistamientoAnonimo) -> AvistamientoAnonimo:
        with self._sf() as s:
            m = AvistamientoModel(
                codigo=a.codigo, especie=a.especie, descripcion=a.descripcion, foto=a.foto,
                lat=a.ubicacion.lat, lon=a.ubicacion.lon, zona=a.zona, fecha=a.fecha,
            )
            s.add(m)
            s.commit()
            a.id = m.id
        return a

    def listar(self, desde: Optional[datetime] = None) -> list[AvistamientoAnonimo]:
        stmt = select(AvistamientoModel).order_by(AvistamientoModel.fecha.desc())
        if desde:
            stmt = stmt.where(AvistamientoModel.fecha >= desde)
        with self._sf() as s:
            return [self._dom(m) for m in s.scalars(stmt)]


class SqlNotificacionRepository(INotificacionRepository):
    def __init__(self, sf):
        self._sf = sf

    def add(self, n: Notificacion) -> Notificacion:
        with self._sf() as s:
            m = NotificacionModel(
                usuario_id=n.usuario_id, reporte_id=n.reporte_id, mensaje=n.mensaje,
                distancia_km=n.distancia_km, lat=n.lat, lon=n.lon, leida=n.leida, creada_en=n.creada_en,
            )
            s.add(m)
            s.commit()
            n.id = m.id
        return n

    def de_usuario(self, usuario_id: int) -> list[Notificacion]:
        stmt = (
            select(NotificacionModel)
            .where(NotificacionModel.usuario_id == usuario_id)
            .order_by(NotificacionModel.creada_en.desc(), NotificacionModel.id.desc())
        )
        with self._sf() as s:
            return [
                Notificacion(m.usuario_id, m.reporte_id, m.mensaje, m.distancia_km, m.lat, m.lon,
                             m.leida, m.id, m.creada_en)
                for m in s.scalars(stmt)
            ]

    def no_leidas(self, usuario_id: int) -> int:
        stmt = select(func.count()).select_from(NotificacionModel).where(
            NotificacionModel.usuario_id == usuario_id, NotificacionModel.leida.is_(False)
        )
        with self._sf() as s:
            return s.scalar(stmt) or 0

    def marcar_leidas(self, usuario_id: int) -> None:
        with self._sf() as s:
            s.execute(
                update(NotificacionModel)
                .where(NotificacionModel.usuario_id == usuario_id)
                .values(leida=True)
            )
            s.commit()