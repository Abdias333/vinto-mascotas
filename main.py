from nicegui import app, ui

from mascotas import config
from mascotas.ui import pages  # noqa: F401  (registra las páginas)

config.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.add_static_files("/media", str(config.MEDIA_DIR))

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="Vinto Mascotas",
        host="0.0.0.0",
        port=config.PORT,
        reload=False,
        show=False,
        storage_secret=config.STORAGE_SECRET,
        favicon=str(config.BASE_DIR / "mascotas" / "ui" / "static" / "favicon.svg"),
    )
