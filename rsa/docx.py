"""Opportunity Brief en Word (.docx) sin dependencias (WordprocessingML con zipfile).
Membrete con el logo de marca/logo.png SOLO si existe localmente (no se versiona) + aviso de prototipo."""
from __future__ import annotations

import io
import zipfile
from datetime import datetime
from xml.sax.saxutils import escape

BLUE, ORANGE, GREY, RED = "002A8D", "FF7800", "5B6787", "C0392B"
ETQ = {"hecho": "Hechos confirmados", "hipotesis": "Hipótesis", "faltante": "Datos faltantes",
       "correccion": "Correcciones", "advertencia": "Advertencias"}


def _run(text, b=False, color=None, size=None, i=False):
    pr = ("<w:b/>" if b else "") + ("<w:i/>" if i else "") + (f'<w:color w:val="{color}"/>' if color else "") + \
         (f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>' if size else "")
    return f'<w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>{pr}</w:rPr>' \
           f'<w:t xml:space="preserve">{escape(str(text))}</w:t></w:r>'


def _p(*runs, after=80, before=0, ind=0, shade=None, align=None, keep=False):
    ppr = f'<w:spacing w:before="{before}" w:after="{after}"/>' + (f'<w:ind w:left="{ind}"/>' if ind else "") + \
          (f'<w:shd w:val="clear" w:color="auto" w:fill="{shade}"/>' if shade else "") + \
          (f'<w:jc w:val="{align}"/>' if align else "") + ("<w:keepNext/>" if keep else "")
    return f"<w:p><w:pPr>{ppr}</w:pPr>{''.join(runs)}</w:p>"


def _h(text, color=BLUE, size=26, before=240):
    return _p(_run(text, b=True, color=color, size=size), before=before, after=80, keep=True)


def _bullet(text, sid=None, extra=None, mark="•"):
    runs = [_run(f"{mark}  ", color=GREY), _run(text)]
    if extra:
        runs.append(_run(f"  {extra}", i=True, color=RED, size=18))
    if sid:
        runs.append(_run(f"  [{sid}]", b=True, color=BLUE, size=18))
    return _p(*runs, ind=280, after=60)


def _table(rows, widths, header=True, fill="EEF2FB"):
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    out = []
    for ri, row in enumerate(rows):
        cells = []
        for ci, val in enumerate(row):
            sh = f'<w:shd w:val="clear" w:color="auto" w:fill="{BLUE if header and ri == 0 else fill}"/>'
            col = "FFFFFF" if header and ri == 0 else None
            cells.append(f'<w:tc><w:tcPr><w:tcW w:w="{widths[ci]}" w:type="dxa"/>{sh}</w:tcPr>'
                         f'{_p(_run(val, b=header and ri == 0, color=col, size=18), after=40)}</w:tc>')
        out.append(f"<w:tr>{''.join(cells)}</w:tr>")
    borders = "".join(f'<w:{b} w:val="single" w:sz="4" w:color="E3E8F2"/>' for b in
                      ("top", "left", "bottom", "right", "insideH", "insideV"))
    return f'<w:tbl><w:tblPr><w:tblW w:w="{sum(widths)}" w:type="dxa"/><w:tblBorders>{borders}</w:tblBorders>' \
           f'<w:tblCellMar><w:left w:w="100" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tblCellMar></w:tblPr>' \
           f'<w:tblGrid>{grid}</w:tblGrid>{"".join(out)}</w:tbl>'


def _logo_drawing(cx, cy):
    return (f'<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/>'
            f'<wp:docPr id="1" name="Logo"/><a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:pic><pic:nvPicPr><pic:cNvPr id="1" name="logo.png"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="rIdLogo"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
            f'</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>')


NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
      'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"')


def _logo_size(png: bytes, height_emu=380000):
    w = int.from_bytes(png[16:20], "big") or 1
    h = int.from_bytes(png[20:24], "big") or 1
    return int(height_emu * w / h), height_emu


def build(sig, fuentes: dict, ver: dict, logo: bytes | None = None) -> bytes:
    C = sig["componentes"]
    act = [c for c in sig["claims"] if not c.get("superada")]
    motor = (ver.get("motor") or {}).get("modo", "reglas")
    body = []
    body.append(_p(_run("OPPORTUNITY BRIEF", b=True, color=ORANGE, size=18), after=0))
    body.append(_p(_run(f"{sig['id']} · {sig['titulo']}", b=True, color=BLUE, size=36), after=60))
    body.append(_p(_run(f"Versión v{ver['v']} · {ver['evento']} · generado {datetime.now():%d/%m/%Y %H:%M} · "
                        f"motor: {'Claude decide, reglas auditan' if motor == 'claude' else 'reglas'}", color=GREY, size=18),
                   after=160))
    body.append(_table([["Score", "Recomendación", "Madurez de evidencia", "Áreas"],
                        [f"{sig['score']} / 100", sig.get("recomendacion", ""), sig["confianza"], ", ".join(sig["areas"])]],
                       [1300, 3900, 1700, 2460]))
    body.append(_p(after=60))
    body.append(_table([["Impacto (45 %)", "Evidencia (30 %)", "Urgencia (25 %)", "Penalización"],
                        [str(C["impacto"]), str(C["evidencia"]), str(C["urgencia"]), f"−{C.get('penalizacion', 0)}"]],
                       [2340, 2340, 2340, 2340]))
    if sig.get("resumen_llm"):
        body.append(_h("Resumen ejecutivo"))
        body.append(_p(_run(sig["resumen_llm"]), shade="EEF2FB", after=80))
    if sig["no_afirmo"]:
        body.append(_h("Lo que NO afirmo", color=RED))
        body += [_bullet(m) for m in sig["no_afirmo"]]
    for t in ("hecho", "hipotesis", "faltante", "correccion", "advertencia"):
        xs = [c for c in sig["claims"] if c["tipo"] == t]
        rows = [c for c in xs if c["texto"].startswith("Fila ")]
        xs = [c for c in xs if not c["texto"].startswith("Fila ")] + rows[:3]
        if not xs:
            continue
        body.append(_h(f"{ETQ[t]} ({len(xs) + max(0, len(rows) - 3)})"))
        if len(rows) > 3:
            body.append(_p(_run(f"Incluye {len(rows)} filas de tabla; se muestran 3 (detalle completo en la fuente "
                                f"{rows[0]['fuente']}).", i=True, color=GREY, size=18), ind=280))
        for c in xs:
            extra = f"{c['superada']} por [{c['por']}]" if c.get("superada") else (
                f"confirmada por [{c['confirmada_por']}]" if c.get("confirmada_por") else None)
            body.append(_bullet(c["texto"], c["sid"], extra))
    if sig["consultas"]:
        body.append(_h("Consulta a la herramienta local"))
        for c in sig["consultas"]:
            body.append(_bullet(f"consultar_parametros.py {' '.join(c['args'])} → {c['lectura']}"))
        adv = sig["consultas"][0]["resultado"].get("advertencia")
        if adv:
            body.append(_p(_run(f"⚠ {adv}", i=True, color=GREY, size=18), ind=280))
    if sig["proximos_pasos"]:
        body.append(_h("Próximos pasos"))
        body += [_bullet(p["texto"], p["sid"], mark=f"{i}.") for i, p in enumerate(sig["proximos_pasos"], 1)]
    A = sig.get("auditoria") or {}
    if A.get("motor") == "claude":
        body.append(_h("Auditoría Claude vs. reglas"))
        body.append(_p(_run(f"Claude clasificó {A['por_claude']} de {A['oraciones']} oraciones; las reglas coinciden en "
                            f"{A['coinciden']}. Discrepancias: {len(A['discrepancias'])}. Relaciones en disputa: "
                            f"{len(A.get('relaciones_en_disputa') or [])}.", size=20)))
        sids = {c["sid"] for c in sig["claims"]}
        for cm in [c for c in (ver.get("comites") or []) if any(s in c["objeto"] for s in sids)]:
            body.append(_bullet(f"Comité · {cm['objeto']}: juez {'SÍ' if cm['veredicto'] else 'NO'} — {cm['motivo']}"))
    body.append(_h("Fuentes"))
    rows = [["ID", "Fecha", "Tipo", "Área", "Título"]] + [
        [f, fuentes[f]["fecha"], fuentes[f]["tipo"], fuentes[f]["area"], fuentes[f]["titulo"]] for f in sig["fuentes"]]
    body.append(_table(rows, [700, 1200, 1500, 2100, 3860]))
    sect = ('<w:sectPr><w:headerReference w:type="default" r:id="rIdHdr"/><w:footerReference w:type="default" r:id="rIdFtr"/>'
            '<w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1300" w:right="1134" w:bottom="1134" w:left="1134" '
            'w:header="500" w:footer="500"/></w:sectPr>')
    doc = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {NS}><w:body>{"".join(body)}{sect}</w:body></w:document>'

    if logo:
        cx, cy = _logo_size(logo)
        left = _logo_drawing(cx, cy) + _run("     Revenue Signals · Prototipo de reto técnico", b=True, color=BLUE, size=18)
    else:
        left = _run("● ", color=ORANGE) + _run("Revenue Signals · Prototipo de reto técnico", b=True, color=BLUE, size=20)
    hdr = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr {NS}>'
           f'<w:p><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="12" w:space="6" w:color="{ORANGE}"/></w:pBdr>'
           f'<w:spacing w:after="120"/></w:pPr>{left}</w:p></w:hdr>')
    ftr = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr {NS}>'
           + _p(_run("Documento generado automáticamente sobre fuentes ficticias del reto. Cada afirmación cita su oración "
                     "fuente [Fxx.n]. No representa datos, sistemas ni posiciones oficiales de ninguna entidad.",
                     color=GREY, size=14, i=True), align="center", after=0) + "</w:ftr>")
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>'
          '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
          '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>')
    R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    drels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             f'<Relationship Id="rIdHdr" Type="{R}/header" Target="header1.xml"/>'
             f'<Relationship Id="rIdFtr" Type="{R}/footer" Target="footer1.xml"/></Relationships>')
    hrels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             + (f'<Relationship Id="rIdLogo" Type="{R}/image" Target="media/logo.png"/>' if logo else "") + '</Relationships>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
        z.writestr("word/_rels/document.xml.rels", drels)
        z.writestr("word/header1.xml", hdr)
        z.writestr("word/footer1.xml", ftr)
        z.writestr("word/_rels/header1.xml.rels", hrels)
        if logo:
            z.writestr("word/media/logo.png", logo)
    return buf.getvalue()
