"""Generación del afiche en PDF (hoja Carta) con ReportLab."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen import canvas

from mascotas.application.ports import IPdfGenerator
from mascotas.domain.entities import ReporteMascota

ROJO = HexColor("#0a3440")
AMBAR = HexColor("#e0a02f")
GRIS = HexColor("#64748b")


class ReportLabAficheAdapter(IPdfGenerator):
    def __init__(self, media_dir: Path):
        self.media_dir = Path(media_dir)

    def generar_afiche(self, reporte: ReporteMascota, contacto_nombre: str, contacto_telefono: str) -> bytes:
        buf = BytesIO()
        pdf = canvas.Canvas(buf, pagesize=letter)
        W, H = letter
        m = reporte.mascota

        # Cabecera
        pdf.setFillColor(ROJO)
        pdf.rect(0, H - 110, W, 110, stroke=0, fill=1)
        pdf.setFillColor(AMBAR)
        pdf.rect(0, H - 116, W, 6, stroke=0, fill=1)
        pdf.setFillColor(white)
        pdf.setFont("Helvetica-Bold", 64)
        pdf.drawCentredString(W / 2, H - 82, "SE BUSCA")

        # Foto
        bx, bw, bh = 60, W - 120, 300
        by = H - 110 - 25 - bh
        self._dibujar_foto(pdf, m.foto, bx, by, bw, bh)

        # Datos
        pdf.setFillColor(HexColor("#0f172a"))
        pdf.setFont("Helvetica-Bold", 34)
        pdf.drawCentredString(W / 2, by - 38, m.nombre[:30])
        pdf.setFont("Helvetica", 15)
        y = by - 66
        for linea in (
            f"Especie: {m.especie}" + (f"   |   Raza: {m.raza}" if m.raza else ""),
            f"Color: {m.color}" if m.color else None,
            f"Zona: {reporte.zona}",
            f"Visto por última vez: {reporte.fecha_perdida:%d/%m/%Y %H:%M}",
        ):
            if linea:
                pdf.drawCentredString(W / 2, y, linea)
                y -= 21

        if m.descripcion:
            pdf.setFont("Helvetica-Oblique", 12)
            y -= 4
            for linea in simpleSplit(m.descripcion, "Helvetica-Oblique", 12, W - 130)[:4]:
                pdf.drawCentredString(W / 2, y, linea)
                y -= 15

        # Contacto
        pdf.setFillColor(HexColor("#eef4f5"))
        pdf.setStrokeColor(ROJO)
        pdf.setLineWidth(2)
        pdf.roundRect(60, 48, W - 120, 82, 12, stroke=1, fill=1)
        pdf.setFillColor(ROJO)
        pdf.setFont("Helvetica-Bold", 15)
        pdf.drawCentredString(W / 2, 108, "¿LA VISTE? COMUNÍCATE CON")
        pdf.setFillColor(HexColor("#0f172a"))
        pdf.setFont("Helvetica-Bold", 20)
        pdf.drawCentredString(W / 2, 82, contacto_nombre[:40])
        pdf.setFont("Helvetica-Bold", 22)
        pdf.drawCentredString(W / 2, 58, f"Tel: {contacto_telefono}" if contacto_telefono else "")

        pdf.setFillColor(GRIS)
        pdf.setFont("Helvetica", 9)
        pdf.drawCentredString(W / 2, 28, f"Vinto Mascotas · Red comunitaria de búsqueda · Reporte #{reporte.id}")
        pdf.showPage()
        pdf.save()
        return buf.getvalue()

    def _dibujar_foto(self, pdf, foto, x, y, w, h) -> None:
        try:
            if not foto:
                raise FileNotFoundError
            img = ImageReader(str(self.media_dir / foto))
            iw, ih = img.getSize()
            esc = min(w / iw, h / ih)
            dw, dh = iw * esc, ih * esc
            pdf.drawImage(img, x + (w - dw) / 2, y + (h - dh) / 2, dw, dh)
        except Exception:
            pdf.setFillColor(HexColor("#e2e8f0"))
            pdf.rect(x, y, w, h, stroke=0, fill=1)
            pdf.setFillColor(GRIS)
            pdf.setFont("Helvetica", 18)
            pdf.drawCentredString(x + w / 2, y + h / 2, "Sin foto")
