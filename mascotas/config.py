"""Configuración central. Todo se lee desde el archivo .env."""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _database_url():
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    return URL.create(
        "postgresql+psycopg2",
        username=os.getenv("POSTGRES_USER", "vinto"),
        password=os.getenv("POSTGRES_PASSWORD", "vinto123"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        database=os.getenv("POSTGRES_DB", "vinto_mascotas"),
    )


def _ruta(valor: str) -> Path:
    p = Path(valor)
    return p if p.is_absolute() else BASE_DIR / p


DATABASE_URL = _database_url()
PORT = int(os.getenv("APP_PORT", "8080"))
STORAGE_SECRET = os.getenv("STORAGE_SECRET", "cambia-esta-clave")
MEDIA_DIR = _ruta(os.getenv("MEDIA_DIR", "media"))

ADMIN_NOMBRE = os.getenv("ADMIN_NOMBRE", "Administrador")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@vinto.bo")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin12345")

CENTRO_LAT = float(os.getenv("CENTRO_LAT", "-17.3917"))
CENTRO_LON = float(os.getenv("CENTRO_LON", "-66.3167"))
RADIO_KM_DEFECTO = float(os.getenv("RADIO_KM_DEFECTO", "1.0"))
ZONAS = [
    z.strip()
    for z in os.getenv(
        "ZONAS", "Vinto Centro,Vinto Norte,Vinto Sur,Vinto Este,Vinto Oeste"
    ).split(",")
    if z.strip()
]
GEOCODER_USER_AGENT = os.getenv("GEOCODER_USER_AGENT", "vinto-mascotas/1.0")
