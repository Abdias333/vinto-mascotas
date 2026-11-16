"""Identidad visual: sobria, institucional, con curvas de nivel como motivo."""
import math

from nicegui import ui

FUENTES = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600'
    '&family=Source+Serif+4:opsz,wght@8..60,500;8..60,600&display=swap" rel="stylesheet">'
)

CSS = """
<style>
:root{
  --ink:#14262e; --muted:#5b6c74; --paper:#f0f3f2; --surface:#ffffff; --line:#d2dad8;
  --brand:#0f4c5c; --brand-deep:#0a3440; --amber:#c77d0a; --link:#0f4c5c;
  --c-ACTIVO:#955700; --c-COINCIDENCIA_DETECTADA:#2a5d8f; --c-RESCATADO:#2f6f4e; --c-ARCHIVADO:#68767d;
}
body.body--dark{
  --ink:#e6edef; --muted:#9db0b8; --paper:#0b1519; --line:#25373e;
  --surface:#121f25; --link:#6fbfd1; --q-primary:#4ea6bb !important;
  --c-ACTIVO:#e3a640; --c-COINCIDENCIA_DETECTADA:#6aa6dc; --c-RESCATADO:#62b98b; --c-ARCHIVADO:#93a2a9;
}
body{background:var(--paper);color:var(--ink);font-family:'IBM Plex Sans',system-ui,-apple-system,'Segoe UI',sans-serif;}
.q-btn,.q-field,.q-tab,.q-item,.q-table,.q-select{font-family:'IBM Plex Sans',system-ui,sans-serif !important;}
.nicegui-content{padding:0 !important;gap:0 !important;align-items:stretch !important;}

.vm-serif{font-family:'Source Serif 4',Georgia,'Times New Roman',serif;font-weight:600;letter-spacing:-.01em;}
.vm-muted{color:var(--muted);}
.vm-small{font-size:.88rem;color:var(--muted);line-height:1.45;}

/* Cabecera */
.vm-top{background:var(--brand-deep);color:#fff;border-bottom:3px solid var(--amber);}
.vm-top-in{max-width:1120px;margin:0 auto;padding:6px 20px;display:flex;align-items:center;
  justify-content:space-between;min-height:58px;gap:12px;flex-wrap:wrap;}
.vm-brand{color:#fff !important;text-decoration:none !important;font-size:1.3rem;}
.vm-brand small{display:block;font-family:'IBM Plex Sans',sans-serif;font-weight:400;font-size:.72rem;
  color:#9fc0c9;letter-spacing:.01em;margin-top:-2px;}
.vm-nav{color:#d3e4e9 !important;text-decoration:none !important;font-size:.9rem;padding:7px 11px;
  border-radius:3px;background:transparent;border:0;cursor:pointer;font-family:inherit;}
.vm-nav:hover{background:rgba(255,255,255,.12);color:#fff !important;}

/* Estructura */
.vm-wrap{max-width:1120px;margin:0 auto;padding:30px 20px 72px;width:100%;box-sizing:border-box;}
.vm-title{font-size:1.9rem;line-height:1.2;margin:0;}
.vm-lead{color:var(--muted);max-width:64ch;margin-top:6px;line-height:1.55;}
.vm-panel{background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:22px;
  box-shadow:none !important;color:var(--ink);}
.vm-h2{font-size:1.2rem;margin:0 0 4px 0;}
.vm-grid2{display:grid;grid-template-columns:1.4fr 1fr;gap:28px;align-items:start;}
@media (max-width:860px){.vm-grid2{grid-template-columns:1fr;}}

/* Portada */
.vm-hero{background:var(--brand-deep);color:#fff;position:relative;overflow:hidden;}
.vm-hero-in{max-width:1120px;margin:0 auto;padding:72px 20px 80px;position:relative;z-index:1;}
.vm-hero h1{font-size:clamp(2.1rem,4.6vw,3.3rem);line-height:1.08;max-width:17ch;margin:0;}
.vm-hero p{color:#bcd2d8;max-width:54ch;font-size:1.08rem;line-height:1.55;margin:18px 0 28px 0;}
.vm-contours{position:absolute;right:-90px;top:-70px;width:820px;max-width:none;color:#2f7284;
  opacity:.55;pointer-events:none;}
.vm-btn-amber{background:#e0a02f !important;color:#10232a !important;font-weight:600;border-radius:4px !important;}
.vm-btn-ghost{border:1px solid rgba(255,255,255,.55) !important;color:#fff !important;border-radius:4px !important;}

/* Libro de situación y pasos */
.vm-row{display:flex;justify-content:space-between;align-items:baseline;padding:11px 0;
  border-bottom:1px solid var(--line);gap:12px;}
.vm-row:last-child{border-bottom:0;}
.vm-val{font-family:'Source Serif 4',Georgia,serif;font-weight:600;font-size:1.25rem;}
.vm-step{display:grid;grid-template-columns:34px 1fr;gap:14px;padding:12px 0;}
.vm-stepn{width:28px;height:28px;border:1.5px solid var(--brand);color:var(--brand);display:grid;
  place-items:center;font-weight:600;border-radius:3px;font-size:.9rem;}
body.body--dark .vm-stepn{border-color:var(--link);color:var(--link);}

/* Estados */
.vm-chip{display:inline-flex;align-items:center;gap:6px;font-size:.76rem;font-weight:500;
  padding:2px 9px;border-radius:3px;border:1px solid currentColor;white-space:nowrap;}
.vm-chip::before{content:"";width:6px;height:6px;border-radius:50%;background:currentColor;}
.vm-c-ACTIVO{color:var(--c-ACTIVO);} .vm-c-COINCIDENCIA_DETECTADA{color:var(--c-COINCIDENCIA_DETECTADA);}
.vm-c-RESCATADO{color:var(--c-RESCATADO);} .vm-c-ARCHIVADO{color:var(--c-ARCHIVADO);}

/* Registros (listas) */
.vm-item{display:grid;grid-template-columns:96px 1fr auto;gap:18px;padding:18px 0;
  border-bottom:1px solid var(--line);align-items:start;}
.vm-item:last-child{border-bottom:0;}
.vm-thumb{width:96px;height:96px;object-fit:cover;border-radius:4px;background:var(--line);}
.vm-nothumb{display:grid;place-items:center;font-size:.72rem;color:var(--muted);}
.vm-actions{display:flex;flex-direction:column;gap:8px;align-items:stretch;min-width:180px;}
@media (max-width:700px){
  .vm-item{grid-template-columns:72px 1fr;} .vm-thumb{width:72px;height:72px;}
  .vm-actions{grid-column:1 / -1;flex-direction:row;flex-wrap:wrap;}
}

/* Indicadores del panel de administración */
.vm-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));background:var(--surface);
  border:1px solid var(--line);border-radius:6px;}
.vm-kpi{padding:16px 20px;border-right:1px solid var(--line);}
.vm-kpi:last-child{border-right:0;}
.vm-kpi .vm-val{font-size:1.7rem;display:block;margin-top:2px;}

.vm-leyenda{display:flex;gap:18px;flex-wrap:wrap;font-size:.88rem;color:var(--muted);}
.vm-leyenda i{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:7px;vertical-align:-1px;}
.vm-note{border-left:3px solid var(--amber);padding:8px 14px;background:rgba(199,125,10,.08);
  border-radius:0 4px 4px 0;}
.q-table thead th{font-weight:600;}
</style>
"""


def _contornos() -> str:
    """Curvas de nivel generadas: alusión al relieve del valle y a la cartografía."""
    trazos = []
    for i in range(1, 16):
        r = 34 + i * 25
        pts = []
        for k in range(0, 141):
            a = k / 140 * 2 * math.pi
            rr = r * (1 + 0.10 * math.sin(3 * a + i * 0.33) + 0.055 * math.sin(5 * a - i * 0.21)
                      + 0.025 * math.sin(9 * a + i))
            pts.append(f"{380 + rr * 1.22 * math.cos(a):.1f},{380 + rr * 0.84 * math.sin(a):.1f}")
        trazos.append(f'<polygon points="{" ".join(pts)}"/>')
    return (
        '<svg class="vm-contours" viewBox="0 0 760 760" fill="none" stroke="currentColor" '
        f'stroke-width="1.2" aria-hidden="true">{"".join(trazos)}</svg>'
    )


CONTORNOS_SVG = _contornos()


def aplicar_tema() -> None:
    ui.add_head_html(FUENTES + CSS, shared=True)
