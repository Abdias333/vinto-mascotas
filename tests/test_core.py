"""Pruebas del dominio y de los casos de uso (sin base de datos ni interfaz)."""
from datetime import datetime, timedelta

import pytest

from mascotas.application.distance import HaversineStrategy, ManhattanStrategy
from mascotas.application.ports import (
    IAvistamientoRepository,
    INotificacionRepository,
    IPasswordHasher,
    IReporteRepository,
    IUsuarioRepository,
)
from mascotas.application.services import AuthService, MatchingService, ReporteService
from mascotas.domain.entities import Coordenadas, EstadoReporte, Rol
from mascotas.domain.errors import (
    CredencialesInvalidas,
    PermisoDenegado,
    TransicionInvalida,
    ValidacionError,
)
from mascotas.domain.factory import ReporteFactory
from mascotas.infrastructure.storage import FotoStorage


# ---------- repositorios en memoria (adaptadores de prueba) ----------
class MemReportes(IReporteRepository):
    def __init__(self):
        self.items, self.cambios = {}, []

    def add(self, r):
        r.id = len(self.items) + 1
        self.items[r.id] = r
        return r

    def get(self, i):
        return self.items.get(i)

    def actualizar(self, r):
        self.items[r.id] = r

    def listar(self, filtros=None, dueno_id=None, estados=None):
        out = list(self.items.values())
        if dueno_id is not None:
            out = [r for r in out if r.dueno_id == dueno_id]
        if estados:
            out = [r for r in out if r.estado in estados]
        return out

    def registrar_cambio(self, c):
        self.cambios.append(c)

    def historial(self, i):
        return [c for c in self.cambios if c.reporte_id == i]


class MemAvistamientos(IAvistamientoRepository):
    def __init__(self):
        self.items = []

    def add(self, a):
        a.id = len(self.items) + 1
        self.items.append(a)
        return a

    def listar(self, desde=None):
        return [a for a in self.items if not desde or a.fecha >= desde]


class MemNotifs(INotificacionRepository):
    def __init__(self):
        self.items = []

    def add(self, n):
        self.items.append(n)
        return n

    def de_usuario(self, uid):
        return [n for n in self.items if n.usuario_id == uid]

    def no_leidas(self, uid):
        return sum(1 for n in self.de_usuario(uid) if not n.leida)

    def marcar_leidas(self, uid):
        for n in self.de_usuario(uid):
            n.leida = True


class MemUsuarios(IUsuarioRepository):
    def __init__(self):
        self.items = {}

    def add(self, u):
        u.id = len(self.items) + 1
        self.items[u.id] = u
        return u

    def por_email(self, e):
        return next((u for u in self.items.values() if u.email == e), None)

    def get(self, i):
        return self.items.get(i)


class HasherFalso(IPasswordHasher):
    def hashear(self, c):
        return "h:" + c

    def verificar(self, c, h):
        return h == "h:" + c


# ---------------------------- utilidades ----------------------------
CENTRO = (-17.3917, -66.3167)


def datos_reporte(**kw):
    base = dict(dueno_id=1, nombre="Firulais", especie="Perro", raza="Mestizo", color="Café",
                lat=CENTRO[0], lon=CENTRO[1], zona="Vinto Centro", radio_km=1.0)
    return base | kw


def datos_avistamiento(dlat=0.0, **kw):
    base = dict(lat=CENTRO[0] + dlat, lon=CENTRO[1], especie="Perro", zona="Vinto Centro")
    return base | kw


@pytest.fixture
def servicio():
    return ReporteService(MemReportes(), MemAvistamientos(), MemNotifs(), MatchingService(HaversineStrategy()))


# ------------------------------- pruebas -------------------------------
def test_haversine_un_grado_de_latitud():
    d = HaversineStrategy().distancia_km(Coordenadas(0, 0), Coordenadas(1, 0))
    assert d == pytest.approx(111.19, abs=0.1)


def test_estrategias_son_intercambiables():
    a, b = Coordenadas(*CENTRO), Coordenadas(CENTRO[0] + 0.01, CENTRO[1] + 0.01)
    assert HaversineStrategy().distancia_km(a, b) < ManhattanStrategy().distancia_km(a, b)


def test_coordenadas_invalidas():
    with pytest.raises(ValidacionError):
        Coordenadas(120, 0)


def test_factory_valida_campos():
    with pytest.raises(ValidacionError):
        ReporteFactory.crear("MASCOTA_PERDIDA", datos_reporte(nombre=""))
    with pytest.raises(ValidacionError):
        ReporteFactory.crear("MASCOTA_PERDIDA", datos_reporte(lat=None))
    with pytest.raises(ValidacionError):
        ReporteFactory.crear("MASCOTA_PERDIDA", datos_reporte(radio_km=500))
    with pytest.raises(ValidacionError):
        ReporteFactory.crear("INVENTADO", {})


def test_transiciones_de_estado():
    r = ReporteFactory.crear("MASCOTA_PERDIDA", datos_reporte())
    r.cambiar_estado(EstadoReporte.RESCATADO)
    with pytest.raises(TransicionInvalida):
        r.cambiar_estado(EstadoReporte.ACTIVO)


def test_avistamiento_cercano_alerta_y_cambia_estado(servicio):
    reporte = servicio.publicar_reporte(datos_reporte())
    av, n = servicio.registrar_avistamiento(datos_avistamiento(dlat=0.005))  # ~0.55 km
    assert n == 1 and av.codigo
    assert servicio.reportes.get(reporte.id).estado == EstadoReporte.COINCIDENCIA_DETECTADA
    assert servicio.notificaciones.no_leidas(1) == 1
    assert servicio.historial(reporte.id)[0].por == "sistema"


def test_avistamiento_lejano_no_alerta(servicio):
    servicio.publicar_reporte(datos_reporte())
    _, n = servicio.registrar_avistamiento(datos_avistamiento(dlat=0.05))  # ~5.5 km
    assert n == 0


def test_especie_distinta_no_coincide(servicio):
    servicio.publicar_reporte(datos_reporte())
    _, n = servicio.registrar_avistamiento(datos_avistamiento(dlat=0.001, especie="Gato"))
    assert n == 0


def test_reporte_nuevo_detecta_avistamiento_previo(servicio):
    servicio.registrar_avistamiento(datos_avistamiento(dlat=0.002))
    r = servicio.publicar_reporte(datos_reporte())
    assert servicio.reportes.get(r.id).estado == EstadoReporte.COINCIDENCIA_DETECTADA


def test_permisos_cambio_de_estado(servicio):
    r = servicio.publicar_reporte(datos_reporte())
    with pytest.raises(PermisoDenegado):
        servicio.cambiar_estado(r.id, EstadoReporte.RESCATADO, actor_id=99, actor_rol=Rol.DUENO)
    servicio.cambiar_estado(r.id, EstadoReporte.RESCATADO, actor_id=99, actor_rol=Rol.ADMIN)
    assert servicio.reportes.get(r.id).estado == EstadoReporte.RESCATADO


def test_solo_admin_asigna_responsable(servicio):
    r = servicio.publicar_reporte(datos_reporte())
    with pytest.raises(PermisoDenegado):
        servicio.asignar_responsable(r.id, "Cuadrilla 1", Rol.DUENO)
    servicio.asignar_responsable(r.id, "Cuadrilla 1", Rol.ADMIN)
    assert servicio.reportes.get(r.id).responsable == "Cuadrilla 1"


def test_registro_y_login():
    auth = AuthService(MemUsuarios(), HasherFalso())
    auth.registrar("Ana Pérez", "ANA@mail.com", "70012345", "clave12345")
    assert auth.login("ana@mail.com", "clave12345").nombre == "Ana Pérez"
    with pytest.raises(CredencialesInvalidas):
        auth.login("ana@mail.com", "otra")
    with pytest.raises(ValidacionError):
        auth.registrar("Ana", "ana@mail.com", "70012345", "clave12345")  # duplicado
    with pytest.raises(ValidacionError):
        auth.registrar("Luis", "luis@mail.com", "70012345", "corta")


def test_foto_formato_invalido(tmp_path):
    almacen = FotoStorage(tmp_path)
    with pytest.raises(ValidacionError):
        almacen.guardar(b"esto no es una imagen")
    with pytest.raises(ValidacionError):
        almacen.guardar(b"")
