"""Almacenamiento y validación estricta de fotos subidas."""
from __future__ import annotations

import uuid
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from mascotas.domain.errors import ValidacionError

MAX_BYTES = 5 * 1024 * 1024
FORMATOS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


class FotoStorage:
    def __init__(self, media_dir: Path):
        self.media_dir = Path(media_dir)
        self.media_dir.mkdir(parents=True, exist_ok=True)

    def guardar(self, data: bytes) -> str:
        if not data:
            raise ValidacionError("El archivo está vacío")
        if len(data) > MAX_BYTES:
            raise ValidacionError("La imagen supera los 5 MB")
        try:
            with Image.open(BytesIO(data)) as img:
                formato = img.format
                img.verify()
        except (UnidentifiedImageError, OSError):
            raise ValidacionError("El archivo no es una imagen válida") from None
        if formato not in FORMATOS:
            raise ValidacionError("Formato no permitido (usa JPG, PNG o WEBP)")
        nombre = f"{uuid.uuid4().hex}{FORMATOS[formato]}"
        (self.media_dir / nombre).write_bytes(data)
        return nombre
