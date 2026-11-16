"""Interfaz web (NiceGUI). Solo traduce acciones de pantalla a casos de uso."""
from __future__ import annotations

import html
import time
from contextlib import contextmanager
from datetime import datetime

from fastapi.responses import RedirectResponse
from nicegui import app, ui

from mascotas import config
from mascotas.container import Contenedor
from mascotas.domain.entities import TRANSICIONES, EstadoReporte, Rol
from mascotas.domain.errors import DominioError
from mascotas.domain.factory import ESPECIES, ESPECIES_AVISTAMIENTO
from mascotas.ui.theme import CONTORNOS_SVG, aplicar_tema

c = Contenedor()
aplicar_tema()

JS_GPS = """
new Promise((resolve) => {
  if (!navigator.geolocation) { resolve(null); return; }
  navigator.geolocation.getCurrentPosition(
    (p) => resolve([p.coords.latitude, p.coords.longitude]),
    () => resolve(null),
    {enableHighAccuracy: true, timeout: 9000});
});
"""

ACCION_ESTADO = {
    EstadoReporte.ACTIVO: "Reactivar búsqueda",
    EstadoReporte.COINCIDENCIA_DETECTADA: "Registrar coincidencia",
    EstadoReporte.RESCATADO: "Marcar como rescatada",
    EstadoReporte.ARCHIVADO: "Archivar",
}
OPCIONES_ESTADO = {"": "Todos"} | {e.value: e.etiqueta for e in EstadoReporte}
OPCIONES_ZONA = {"": "Todas"} | {z: z for z in config.ZONAS}
OPCIONES_ESPECIE = {"": "Todas"} | {e: e for e in ESPECIES}


# ------------------------------------------------------------------ sesión
def usuario_actual() -> dict | None:
    return app.storage.user.get("usuario")


def _redirigir_si_no_autorizado(roles: tuple[Rol, ...] | None = None):
    u = usuario_actual()
    if not u:
        return RedirectResponse("/login")
    if roles and u["rol"] not in [r.value for r in roles]:
        return RedirectResponse("/")
    return None


# ------------------------------------------------------------------ marco
def _cabecera() -> None:
    u = usuario_actual()
    app.storage.user.setdefault("oscuro", False)
    oscuro = ui.dark_mode().bind_value(app.storage.user, "oscuro")
    ui.colors(primary="#0f4c5c", secondary="#c77d0a", positive="#2f6f4e", negative="#a32a22")
    with ui.element("header").classes("vm-top"):
        with ui.element("div").classes("vm-top-in"):
            with ui.link(target="/").classes("vm-brand vm-serif"):
                ui.html("Vinto Mascotas<small>Red de búsqueda y alerta del Municipio de Vinto</small>")
            with ui.element("nav").classes("flex items-center gap-1 flex-wrap"):
                ui.link("Mapa de búsqueda", "/mapa").classes("vm-nav")
                ui.link("Reportes", "/reportes").classes("vm-nav")
                if u:
                    if u["rol"] == Rol.ADMIN.value:
                        ui.link("Administración", "/admin").classes("vm-nav")
                    else:
                        ui.link("Mi panel", "/panel").classes("vm-nav")
                    ui.link(f"Salir ({u['nombre'].split()[0]})", "/salir").classes("vm-nav")
                else:
                    ui.link("Ingresar", "/login").classes("vm-nav")
                    ui.link("Crear cuenta", "/registro").classes("vm-nav")
                ui.button().props("flat dense no-caps").classes("vm-nav").bind_text_from(
                    oscuro, "value", lambda v: "Modo claro" if v else "Modo oscuro"
                ).on("click", oscuro.toggle)


@contextmanager
def marco(titulo: str | None = None, descripcion: str | None = None):
    _cabecera()
    with ui.element("main").classes("vm-wrap"):
        if titulo:
            with ui.element("div").classes("mb-6"):
                ui.label(titulo).classes("vm-title vm-serif")
                if descripcion:
                    ui.label(descripcion).classes("vm-lead")
        yield


def chip(estado: EstadoReporte) -> None:
    ui.label(estado.etiqueta).classes(f"vm-chip vm-c-{estado.value}")


def campo(etiqueta: str, **kw) -> ui.input:
    return ui.input(etiqueta, **kw).props("outlined dense").classes("w-full")


def seleccion(etiqueta: str, opciones, valor=None) -> ui.select:
    return ui.select(opciones, label=etiqueta, value=valor).props("outlined dense").classes("w-full")


# ---------------------------------------------------------------- widgets
class SelectorUbicacion:
    """Mapa interactivo: clic, GPS del dispositivo o búsqueda de dirección (adapter OSM)."""

    def __init__(self):
        self.coords: tuple[float, float] | None = None
        self.marker = None
        self.mapa = ui.leaflet(center=(config.CENTRO_LAT, config.CENTRO_LON), zoom=15)
        self.mapa.classes("w-full rounded").style("height:340px")
        self.mapa.on("map-click", self._clic)
        self.etiqueta = ui.label("Toca el mapa para marcar el lugar exacto.").classes("vm-small mt-2")
        with ui.row().classes("w-full items-center gap-2 mt-2"):
            ui.button("Usar mi ubicación actual", icon="my_location", on_click=self.gps).props(
                "outline no-caps dense"
            )
            self.direccion = ui.input("Buscar calle o referencia").props("outlined dense").classes("grow")
            self.direccion.on("keydown.enter", self.buscar)
            ui.button("Buscar", on_click=self.buscar).props("outline no-caps dense")

    def fijar(self, lat: float, lon: float, centrar: bool = False) -> None:
        self.coords = (lat, lon)
        if self.marker is None:
            self.marker = self.mapa.marker(latlng=(lat, lon))
        else:
            self.marker.move(lat, lon)
        if centrar:
            self.mapa.set_center((lat, lon))
        self.etiqueta.text = f"Ubicación seleccionada: {lat:.5f}, {lon:.5f}"

    def _clic(self, e) -> None:
        self.fijar(e.args["latlng"]["lat"], e.args["latlng"]["lng"])

    async def gps(self) -> None:
        ui.notify("Obteniendo tu ubicación…")
        try:
            res = await ui.run_javascript(JS_GPS, timeout=12)
        except TimeoutError:
            res = None
        if res:
            self.fijar(res[0], res[1], centrar=True)
        else:
            ui.notify("No se pudo obtener tu ubicación. Marca el punto en el mapa.", type="warning")

    def buscar(self) -> None:
        punto = c.geo.geocodificar(self.direccion.value)
        if punto:
            self.fijar(punto.lat, punto.lon, centrar=True)
        else:
            ui.notify("No se encontró esa dirección. Marca el punto en el mapa.", type="warning")


class SelectorFoto:
    def __init__(self, etiqueta: str = "Fotografía (JPG, PNG o WEBP, máx. 5 MB)"):
        self.nombre: str | None = None
        ui.upload(
            label=etiqueta, auto_upload=True, max_file_size=5_000_000,
            on_upload=self._subida,
            on_rejected=lambda: ui.notify("Archivo rechazado: revisa el tamaño y el formato", type="negative"),
        ).props("flat bordered accept=image/*").classes("w-full")
        self.estado = ui.label("Aún no se ha cargado ninguna foto.").classes("vm-small mt-1")

    def _subida(self, e) -> None:
        try:
            self.nombre = c.storage.guardar(e.content.read())
            self.estado.text = "Fotografía cargada correctamente."
            ui.notify("Fotografía cargada", type="positive")
        except DominioError as ex:
            self.nombre = None
            self.estado.text = "La fotografía no es válida."
            ui.notify(str(ex), type="negative")


def _miniatura(foto: str | None) -> None:
    if foto:
        ui.image(f"/media/{foto}").classes("vm-thumb")
    else:
        ui.label("Sin foto").classes("vm-thumb vm-nothumb")


def abrir_afiche(reporte_id: int) -> None:
    try:
        pdf = c.afiches.generar(reporte_id)
    except DominioError as e:
        ui.notify(str(e), type="negative")
        return
    carpeta = config.MEDIA_DIR / "afiches"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / f"reporte_{reporte_id}.pdf").write_bytes(pdf)
    ui.navigate.to(f"/media/afiches/reporte_{reporte_id}.pdf?v={int(time.time())}", new_tab=True)


def fila_reporte(r, acciones=None) -> None:
    m = r.mascota
    with ui.element("div").classes("vm-item"):
        _miniatura(m.foto)
        with ui.element("div"):
            with ui.row().classes("items-center gap-3"):
                ui.label(m.nombre).classes("vm-serif text-xl")
                chip(r.estado)
            detalle = m.especie + (f", {m.raza}" if m.raza else "") + (f", color {m.color}" if m.color else "")
            ui.label(detalle).classes("vm-muted")
            ui.label(f"{r.zona}. Perdido el {r.fecha_perdida:%d/%m/%Y a las %H:%M}.").classes("vm-small")
            if m.descripcion:
                ui.label(m.descripcion).classes("vm-small")
            if r.responsable:
                ui.label(f"Responsable asignado: {r.responsable}").classes("vm-small")
        with ui.element("div").classes("vm-actions"):
            ui.button("Descargar afiche PDF", on_click=lambda r=r: abrir_afiche(r.id)).props(
                "outline no-caps dense"
            )
            if acciones:
                acciones(r)


# ----------------------------------------------------------------- portada
@ui.page("/")
def inicio():
    s = c.estadisticas.resumen()
    _cabecera()
    with ui.element("section").classes("vm-hero"):
        ui.html(CONTORNOS_SVG)
        with ui.element("div").classes("vm-hero-in"):
            ui.label("Una red de vecinos para que cada mascota perdida vuelva a casa").classes(
                "vm-serif"
            ).style("font-size:clamp(2.1rem,4.6vw,3.3rem);line-height:1.08;max-width:17ch")
            ui.label(
                "Reporta una pérdida, avisa de un avistamiento y coordina la búsqueda con "
                "ubicación exacta en el Municipio de Vinto, Cochabamba."
            ).style("color:#bcd2d8;max-width:54ch;font-size:1.08rem;line-height:1.55;margin:18px 0 28px")
            with ui.row().classes("gap-3"):
                ui.button("Reportar mascota perdida", on_click=lambda: ui.navigate.to("/reportar")).props(
                    "unelevated no-caps"
                ).classes("vm-btn-amber")
                ui.button("Registrar un avistamiento", on_click=lambda: ui.navigate.to("/avistamiento")).props(
                    "outline no-caps"
                ).classes("vm-btn-ghost")
    with ui.element("main").classes("vm-wrap"):
        with ui.element("div").classes("vm-grid2"):
            with ui.element("div"):
                ui.label("Cómo funciona").classes("vm-h2 vm-serif")
                pasos = [
                    ("El dueño publica la búsqueda",
                     "Registra a su mascota con fotografía, rasgos y el punto donde la perdió, "
                     "y define el radio de alerta."),
                    ("Cualquier vecino puede avisar",
                     "Un avistamiento se envía desde el celular en tres pasos, sin crear una cuenta."),
                    ("El sistema cruza la información",
                     "Si el avistamiento cae dentro del radio, se calcula la distancia exacta y el dueño recibe la alerta."),
                    ("Se imprime y se difunde",
                     "El afiche en PDF, listo para hoja carta, se genera automáticamente con los datos de contacto."),
                ]
                for i, (t, d) in enumerate(pasos, 1):
                    with ui.element("div").classes("vm-step"):
                        ui.label(str(i)).classes("vm-stepn")
                        with ui.element("div"):
                            ui.label(t).classes("font-medium")
                            ui.label(d).classes("vm-small")
            with ui.element("div").classes("vm-panel"):
                ui.label("Situación actual").classes("vm-h2 vm-serif")
                for etiqueta, valor in [
                    ("Búsquedas activas", s["activos"]),
                    ("Avistamientos registrados", s["avistamientos"]),
                    ("Mascotas recuperadas", s["rescatados"]),
                    ("Tasa de recuperación", f"{s['tasa_recuperacion']}%"),
                ]:
                    with ui.element("div").classes("vm-row"):
                        ui.label(etiqueta).classes("vm-muted")
                        ui.label(str(valor)).classes("vm-val")
                ui.button("Abrir el mapa de búsqueda", on_click=lambda: ui.navigate.to("/mapa")).props(
                    "outline no-caps"
                ).classes("w-full mt-3")


# ------------------------------------------------------------ autenticación
@ui.page("/login")
def login():
    if usuario_actual():
        return RedirectResponse("/")
    with marco("Ingresar", "Accede para gestionar tus reportes y consultar tus alertas."):
        with ui.element("div").classes("vm-panel").style("max-width:440px"):
            email = campo("Correo electrónico")
            clave = campo("Contraseña", password=True, password_toggle_button=True).classes("mt-3")

            def entrar():
                try:
                    u = c.auth.login(email.value, clave.value)
                except DominioError as e:
                    ui.notify(str(e), type="negative")
                    return
                app.storage.user["usuario"] = {"id": u.id, "nombre": u.nombre, "rol": u.rol.value}
                ui.navigate.to("/admin" if u.rol == Rol.ADMIN else "/panel")

            clave.on("keydown.enter", entrar)
            ui.button("Ingresar", on_click=entrar).props("unelevated no-caps").classes("w-full mt-4").mark("btn-entrar")
            ui.link("¿No tienes cuenta? Regístrate", "/registro").classes("vm-small mt-3")


@ui.page("/registro")
def registro():
    if usuario_actual():
        return RedirectResponse("/")
    with marco("Crear cuenta de dueño", "Necesitas una cuenta para publicar la búsqueda de tu mascota."):
        with ui.element("div").classes("vm-panel").style("max-width:440px"):
            nombre = campo("Nombre completo")
            email = campo("Correo electrónico").classes("mt-3")
            tel = campo("Teléfono de contacto (aparecerá en el afiche)").classes("mt-3")
            clave = campo("Contraseña (mínimo 8 caracteres)", password=True, password_toggle_button=True).classes("mt-3")

            def crear():
                try:
                    c.auth.registrar(nombre.value, email.value, tel.value, clave.value)
                    u = c.auth.login(email.value, clave.value)
                except DominioError as e:
                    ui.notify(str(e), type="negative")
                    return
                app.storage.user["usuario"] = {"id": u.id, "nombre": u.nombre, "rol": u.rol.value}
                ui.navigate.to("/panel")

            ui.button("Crear cuenta", on_click=crear).props("unelevated no-caps").classes("w-full mt-4").mark("btn-crear")


@ui.page("/salir")
def salir():
    app.storage.user.clear()
    return RedirectResponse("/")


# ------------------------------------------------- reporte de mascota perdida
@ui.page("/reportar")
def reportar():
    if (r := _redirigir_si_no_autorizado()):
        return r
    u = usuario_actual()
    with marco("Reportar mascota perdida",
               "Mientras más precisa sea la información, más rápido podrá actuar la comunidad."):
        with ui.element("div").classes("vm-grid2"):
            with ui.element("div").classes("vm-panel"):
                ui.label("Datos de la mascota").classes("vm-h2 vm-serif")
                nombre = campo("Nombre").classes("mt-3")
                with ui.row().classes("w-full no-wrap gap-3 mt-3"):
                    especie = seleccion("Especie", list(ESPECIES), "Perro")
                    raza = campo("Raza")
                color = campo("Color").classes("mt-3")
                desc = ui.textarea("Características particulares (collar, cicatrices, comportamiento)").props(
                    "outlined dense autogrow"
                ).classes("w-full mt-3")
                ui.label("Fotografía").classes("mt-4 font-medium")
                foto = SelectorFoto()
                with ui.row().classes("w-full no-wrap gap-3 mt-4"):
                    fecha = campo("Fecha y hora de la pérdida", value=datetime.now().strftime("%Y-%m-%dT%H:%M"))
                    fecha.props("type=datetime-local")
                with ui.row().classes("w-full no-wrap gap-3 mt-3"):
                    zona = seleccion("Zona de Vinto", list(config.ZONAS), config.ZONAS[0])
                    radio = ui.number("Radio de alerta (km)", value=config.RADIO_KM_DEFECTO, min=0.1, max=20, step=0.1).props(
                        "outlined dense"
                    ).classes("w-full")
            with ui.element("div").classes("vm-panel"):
                ui.label("Última ubicación conocida").classes("vm-h2 vm-serif")
                ui.label("Se usará para calcular qué avistamientos están dentro del radio.").classes("vm-small mb-3")
                ubic = SelectorUbicacion()

        def publicar():
            try:
                datos = dict(
                    dueno_id=u["id"], nombre=nombre.value, especie=especie.value, raza=raza.value,
                    color=color.value, descripcion=desc.value, foto=foto.nombre,
                    lat=ubic.coords[0] if ubic.coords else None, lon=ubic.coords[1] if ubic.coords else None,
                    zona=zona.value, fecha=fecha.value, radio_km=radio.value,
                )
                c.reportes.publicar_reporte(datos)
            except DominioError as e:
                ui.notify(str(e), type="negative")
                return
            ui.notify("Reporte publicado. Ya puedes descargar el afiche desde tu panel.", type="positive")
            ui.navigate.to("/panel")

        ui.button("Publicar reporte", on_click=publicar).props("unelevated no-caps").classes("mt-5")


# ------------------------------------------------------ avistamiento anónimo
@ui.page("/avistamiento")
def avistamiento():
    with marco("Registrar un avistamiento",
               "No necesitas cuenta. Completa tres pasos y el dueño será alertado si está cerca."):
        with ui.element("div").style("max-width:760px"):
            with ui.element("div").classes("vm-panel"):
                with ui.element("div").classes("vm-step").style("padding-top:0"):
                    ui.label("1").classes("vm-stepn")
                    with ui.element("div").classes("w-full"):
                        ui.label("Dónde la viste").classes("vm-h2 vm-serif")
                        ubic = SelectorUbicacion()
            with ui.element("div").classes("vm-panel mt-4"):
                with ui.element("div").classes("vm-step").style("padding-top:0"):
                    ui.label("2").classes("vm-stepn")
                    with ui.element("div").classes("w-full"):
                        ui.label("Una fotografía").classes("vm-h2 vm-serif")
                        foto = SelectorFoto("Foto del animal (opcional, pero ayuda mucho)")
            with ui.element("div").classes("vm-panel mt-4"):
                with ui.element("div").classes("vm-step").style("padding-top:0"):
                    ui.label("3").classes("vm-stepn")
                    with ui.element("div").classes("w-full"):
                        ui.label("Detalles y envío").classes("vm-h2 vm-serif")
                        with ui.row().classes("w-full no-wrap gap-3 mt-3"):
                            especie = seleccion("Especie", list(ESPECIES_AVISTAMIENTO), "Desconocida")
                            zona = seleccion("Zona", list(config.ZONAS), config.ZONAS[0])
                        desc = ui.textarea("Descripción breve (color, collar, estado)").props(
                            "outlined dense autogrow"
                        ).classes("w-full mt-3")

                        def enviar():
                            try:
                                av, n = c.reportes.registrar_avistamiento(dict(
                                    lat=ubic.coords[0] if ubic.coords else None,
                                    lon=ubic.coords[1] if ubic.coords else None,
                                    especie=especie.value, zona=zona.value,
                                    descripcion=desc.value, foto=foto.nombre,
                                ))
                            except DominioError as e:
                                ui.notify(str(e), type="negative")
                                return
                            with ui.dialog().props("persistent") as dlg, ui.element("div").classes("vm-panel"):
                                ui.label("Avistamiento registrado").classes("vm-h2 vm-serif")
                                ui.label(f"Código de seguimiento: {av.codigo}").classes("font-medium mt-2")
                                ui.label(
                                    f"Se alertó a {n} dueño(s) con una búsqueda activa cerca de ese punto."
                                    if n else
                                    "Por ahora no hay búsquedas activas dentro de ese radio. "
                                    "Si aparece una, el dueño será alertado igualmente."
                                ).classes("vm-small mt-1").style("max-width:340px")
                                ui.button("Cerrar", on_click=lambda: ui.navigate.to("/")).props(
                                    "unelevated no-caps"
                                ).classes("mt-4")
                            dlg.open()

                        ui.button("Enviar avistamiento", on_click=enviar).props("unelevated no-caps").classes("mt-4")


# --------------------------------------------------------------------- mapa
def _marcador(mapa, lat, lon, color, popup, radio_m=None):
    if radio_m:
        mapa.generic_layer(name="circle", args=[(lat, lon), {
            "radius": radio_m, "color": color,
            "weight": 1, "fillColor": color, "fillOpacity": 0.07}])
    capa = mapa.generic_layer(name="circleMarker", args=[(lat, lon), {
        "radius": 9, "color": "#ffffff", "weight": 2, "fillColor": color, "fillOpacity": 1}])
    try:
        capa.run_method("bindPopup", popup)
    except Exception:
        pass


@ui.page("/mapa")
def mapa_busqueda(lat: float | None = None, lon: float | None = None):
    activos = c.reportes.buscar(estados=[EstadoReporte.ACTIVO, EstadoReporte.COINCIDENCIA_DETECTADA])
    recientes = c.reportes.avistamientos_recientes(30)
    with marco("Mapa de búsqueda",
               "Búsquedas activas y avistamientos de los últimos 30 días en el Municipio de Vinto."):
        with ui.element("div").classes("vm-leyenda mb-3"):
            ui.html('<span><i style="background:#0f4c5c"></i>Mascota perdida y su radio de alerta</span>')
            ui.html('<span><i style="background:#c77d0a"></i>Avistamiento anónimo</span>')
        centro = (lat, lon) if lat is not None and lon is not None else (config.CENTRO_LAT, config.CENTRO_LON)
        mapa = ui.leaflet(center=centro, zoom=17 if lat is not None else 14).classes("w-full rounded").style(
            "height:68vh;min-height:420px"
        )
        for r in activos:
            m = r.mascota
            pop = (f"<b>{html.escape(m.nombre)}</b><br>{html.escape(m.especie)}"
                   f"{', ' + html.escape(m.raza) if m.raza else ''}<br>{html.escape(r.zona)}<br>"
                   f"Estado: {r.estado.etiqueta}")
            if m.foto:
                pop += f'<br><img src="/media/{html.escape(m.foto)}" width="140" style="margin-top:6px">'
            _marcador(mapa, r.ubicacion.lat, r.ubicacion.lon, "#0f4c5c", pop, radio_m=r.radio_km * 1000)
        for a in recientes:
            pop = (f"<b>Avistamiento {html.escape(a.codigo)}</b><br>{html.escape(a.especie)}"
                   f"<br>{html.escape(a.zona)}<br>{a.fecha:%d/%m/%Y %H:%M}")
            if a.descripcion:
                pop += f"<br>{html.escape(a.descripcion)}"
            if a.foto:
                pop += f'<br><img src="/media/{html.escape(a.foto)}" width="140" style="margin-top:6px">'
            _marcador(mapa, a.ubicacion.lat, a.ubicacion.lon, "#c77d0a", pop)
        ui.label(f"{len(activos)} búsquedas activas y {len(recientes)} avistamientos recientes.").classes(
            "vm-small mt-2"
        )


# ------------------------------------------------------ consulta con filtros
@ui.page("/reportes")
def reportes_publicos():
    with marco("Reportes de mascotas perdidas", "Consulta los reportes de la comunidad y filtra por características."):
        with ui.element("div").classes("vm-panel mb-4"):
            with ui.row().classes("w-full items-end gap-3"):
                f_especie = seleccion("Especie", OPCIONES_ESPECIE, "").classes("w-40")
                f_raza = campo("Raza").classes("w-40")
                f_color = campo("Color").classes("w-40")
                f_zona = seleccion("Zona", OPCIONES_ZONA, "").classes("w-48")
                f_estado = seleccion("Estado", OPCIONES_ESTADO, "ACTIVO").classes("w-48")
                f_desde = campo("Perdido desde").props("type=date stack-label").classes("w-44")
                f_hasta = campo("Perdido hasta").props("type=date stack-label").classes("w-44")
                ui.button("Aplicar filtros", on_click=lambda: lista.refresh()).props("unelevated no-caps")

        @ui.refreshable
        def lista():
            filtros = dict(especie=f_especie.value, raza=f_raza.value, color=f_color.value,
                           zona=f_zona.value, estado=f_estado.value,
                           desde=f_desde.value, hasta=f_hasta.value)
            datos = c.reportes.buscar(filtros)
            with ui.element("div").classes("vm-panel"):
                ui.label(f"{len(datos)} resultado(s)").classes("vm-small")
                if not datos:
                    ui.label("No hay reportes con esos criterios.").classes("vm-muted py-6")
                for r in datos:
                    fila_reporte(r)

        lista()


# --------------------------------------------------------------- panel dueño
@ui.page("/panel")
def panel_dueno():
    if (r := _redirigir_si_no_autorizado((Rol.DUENO,))):
        return r
    u = usuario_actual()
    sin_leer = c.notificaciones.no_leidas(u["id"])
    with marco("Mi panel", f"Sesión de {u['nombre']}."):
        ui.button("Publicar nuevo reporte", on_click=lambda: ui.navigate.to("/reportar")).props(
            "unelevated no-caps"
        ).classes("mb-4")
        tabs = ui.tabs().props("align=left no-caps inline-label")
        t_rep = ui.tab("Mis reportes")
        t_not = ui.tab(f"Alertas de avistamiento ({sin_leer} sin leer)" if sin_leer else "Alertas de avistamiento")

        @ui.refreshable
        def mis_reportes():
            datos = c.reportes.de_dueno(u["id"])
            with ui.element("div").classes("vm-panel"):
                if not datos:
                    ui.label("Aún no has publicado ningún reporte.").classes("vm-muted py-4")
                for r in datos:
                    fila_reporte(r, acciones=acciones_dueno)
                    with ui.expansion("Historial de estados").classes("w-full text-sm"):
                        cambios = c.reportes.historial(r.id)
                        if not cambios:
                            ui.label("Sin cambios registrados.").classes("vm-small")
                        for ch in cambios:
                            ui.label(f"{ch.fecha:%d/%m/%Y %H:%M}  {ch.anterior} a {ch.nuevo}  (por {ch.por})").classes("vm-small")

        def cambiar(reporte_id: int, nuevo: EstadoReporte):
            try:
                c.reportes.cambiar_estado(reporte_id, nuevo, u["id"], Rol(u["rol"]))
            except DominioError as e:
                ui.notify(str(e), type="negative")
                return
            ui.notify("Estado actualizado", type="positive")
            mis_reportes.refresh()

        def acciones_dueno(r):
            for nuevo in sorted(TRANSICIONES[r.estado], key=lambda e: e.value):
                b = ui.button(ACCION_ESTADO[nuevo], on_click=lambda r=r, n=nuevo: cambiar(r.id, n))
                b.props("no-caps dense " + ("unelevated" if nuevo == EstadoReporte.RESCATADO else "flat"))

        @ui.refreshable
        def bandeja():
            notifs = c.notificaciones.bandeja(u["id"])
            with ui.element("div").classes("vm-panel"):
                if not notifs:
                    ui.label("No tienes alertas. Te avisaremos cuando alguien vea una mascota cerca de donde se perdió la tuya.").classes("vm-muted py-4")
                else:
                    ui.button("Marcar todas como leídas", on_click=leer).props("outline no-caps dense").classes("mb-2")
                for n in notifs:
                    with ui.element("div").classes("vm-row").style("align-items:flex-start"):
                        with ui.element("div"):
                            ui.label(n.mensaje).classes("font-medium" if not n.leida else "vm-muted")
                            ui.label(f"{n.creada_en:%d/%m/%Y %H:%M}").classes("vm-small")
                        if n.lat is not None:
                            ui.button("Ver en el mapa", on_click=lambda n=n: ui.navigate.to(f"/mapa?lat={n.lat}&lon={n.lon}")).props(
                                "outline no-caps dense"
                            )

        def leer():
            c.notificaciones.marcar_leidas(u["id"])
            bandeja.refresh()

        with ui.tab_panels(tabs, value=t_rep).classes("w-full").style("background:transparent"):
            with ui.tab_panel(t_rep).style("padding:16px 0"):
                mis_reportes()
            with ui.tab_panel(t_not).style("padding:16px 0"):
                bandeja()


# ------------------------------------------------------- administración
@ui.page("/admin")
def administracion():
    if (r := _redirigir_si_no_autorizado((Rol.ADMIN,))):
        return r
    u = usuario_actual()

    with marco("Panel de administración", "Supervisión de reportes, estados, responsables y métricas."):
        @ui.refreshable
        def indicadores():
            s = c.estadisticas.resumen()
            h = s["horas_primera_coincidencia"]
            items = [
                ("Reportes totales", s["total"]),
                ("Búsquedas activas", s["activos"]),
                ("Rescatadas", s["rescatados"]),
                ("Tasa de recuperación", f"{s['tasa_recuperacion']}%"),
                ("Tiempo medio hasta la primera coincidencia", f"{h} h" if h is not None else "Sin datos"),
                ("Avistamientos", s["avistamientos"]),
            ]
            with ui.element("div").classes("vm-kpis"):
                for et, val in items:
                    with ui.element("div").classes("vm-kpi"):
                        ui.label(et).classes("vm-small")
                        ui.label(str(val)).classes("vm-val")
            with ui.element("div").classes("vm-panel mt-4"):
                ui.label("Zonas con más reportes").classes("vm-h2 vm-serif")
                zonas = s["zonas_criticas"]
                if zonas:
                    eje = {"axisLabel": {"color": "#7d8f96"}, "axisLine": {"lineStyle": {"color": "#7d8f96"}}}
                    ui.echart({
                        "grid": {"left": 40, "right": 16, "top": 16, "bottom": 36},
                        "xAxis": {"type": "category", "data": [z for z, _ in zonas], **eje},
                        "yAxis": {"type": "value", "minInterval": 1, **eje,
                                  "splitLine": {"lineStyle": {"color": "rgba(125,143,150,.25)"}}},
                        "series": [{"type": "bar", "data": [n for _, n in zonas],
                                    "itemStyle": {"color": "#0f4c5c"}, "barMaxWidth": 46}],
                    }).classes("w-full").style("height:240px")
                else:
                    ui.label("Todavía no hay reportes.").classes("vm-muted py-3")

        indicadores()

        columnas = [
            {"name": "id", "label": "N.º", "field": "id", "align": "left", "sortable": True},
            {"name": "mascota", "label": "Mascota", "field": "mascota", "align": "left", "sortable": True},
            {"name": "especie", "label": "Especie", "field": "especie", "align": "left"},
            {"name": "zona", "label": "Zona", "field": "zona", "align": "left", "sortable": True},
            {"name": "estado", "label": "Estado", "field": "estado", "align": "left", "sortable": True},
            {"name": "responsable", "label": "Responsable", "field": "responsable", "align": "left"},
            {"name": "fecha", "label": "Publicado", "field": "fecha", "align": "left", "sortable": True},
        ]

        def filas():
            return [dict(
                id=r.id, mascota=r.mascota.nombre, especie=r.mascota.especie, zona=r.zona,
                estado=r.estado.etiqueta, estado_raw=r.estado.value,
                responsable=r.responsable or "Sin asignar", fecha=f"{r.creado_en:%d/%m/%Y %H:%M}",
            ) for r in c.reportes.buscar()]

        with ui.element("div").classes("vm-panel mt-4"):
            ui.label("Reportes de la comunidad").classes("vm-h2 vm-serif")
            ui.label("Selecciona un reporte para cambiar su estado, asignar un responsable o revisar su auditoría.").classes("vm-small mb-3")
            tabla = ui.table(columns=columnas, rows=filas(), row_key="id", selection="single",
                             pagination=8).props("flat bordered").classes("w-full")

            with ui.element("div").classes("vm-grid2 mt-5").style("grid-template-columns:1fr 1fr"):
                with ui.element("div"):
                    ui.label("Gestionar el reporte seleccionado").classes("font-medium mb-2")
                    sel_estado = seleccion("Nuevo estado", {}).classes("mb-2")
                    ui.button("Aplicar cambio de estado", on_click=lambda: cambiar_estado()).props(
                        "unelevated no-caps dense"
                    )
                    inp_resp = campo("Responsable (cuadrilla o voluntario)").classes("mt-4 mb-2")
                    ui.button("Guardar responsable", on_click=lambda: asignar()).props("outline no-caps dense")
                with ui.element("div"):
                    ui.label("Auditoría de cambios de estado").classes("font-medium mb-2")

                    @ui.refreshable
                    def auditoria():
                        fila = tabla.selected[0] if tabla.selected else None
                        if not fila:
                            ui.label("Selecciona un reporte para ver su historial.").classes("vm-small")
                            return
                        cambios = c.reportes.historial(fila["id"])
                        if not cambios:
                            ui.label("Este reporte no tiene cambios registrados.").classes("vm-small")
                        for ch in cambios:
                            ui.label(f"{ch.fecha:%d/%m/%Y %H:%M}  {ch.anterior} a {ch.nuevo}  (por {ch.por})").classes("vm-small")

                    auditoria()

        def seleccionado():
            return tabla.selected[0] if tabla.selected else None

        def al_seleccionar():
            fila = seleccionado()
            if fila:
                actual = EstadoReporte(fila["estado_raw"])
                sel_estado.set_options({e.value: e.etiqueta for e in sorted(TRANSICIONES[actual], key=lambda e: e.value)}, value=None)
                inp_resp.value = "" if fila["responsable"] == "Sin asignar" else fila["responsable"]
            else:
                sel_estado.set_options({}, value=None)
                inp_resp.value = ""
            auditoria.refresh()

        tabla.on("selection", al_seleccionar)

        def recargar():
            tabla.rows = filas()
            tabla.selected.clear()
            tabla.update()
            al_seleccionar()
            indicadores.refresh()

        def cambiar_estado():
            fila = seleccionado()
            if not fila or not sel_estado.value:
                ui.notify("Selecciona un reporte y el nuevo estado", type="warning")
                return
            try:
                c.reportes.cambiar_estado(fila["id"], EstadoReporte(sel_estado.value), u["id"], Rol(u["rol"]))
            except DominioError as e:
                ui.notify(str(e), type="negative")
                return
            ui.notify("Estado actualizado", type="positive")
            recargar()

        def asignar():
            fila = seleccionado()
            if not fila:
                ui.notify("Selecciona un reporte", type="warning")
                return
            try:
                c.reportes.asignar_responsable(fila["id"], inp_resp.value, Rol(u["rol"]))
            except DominioError as e:
                ui.notify(str(e), type="negative")
                return
            ui.notify("Responsable guardado", type="positive")
            recargar()