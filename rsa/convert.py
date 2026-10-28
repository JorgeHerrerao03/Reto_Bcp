"""Convierte entradas al formato estándar de fuente del paquete:
.md/.txt/texto pegado · .docx (párrafos y tablas) · .xlsx/.csv/.tsv (filas + cálculos por código) ·
imágenes y PDF (transcripción con Claude, requiere API)."""
from __future__ import annotations

import io
import re
import zipfile
from datetime import date
from xml.etree import ElementTree as ET

HDR = re.compile(r"^\*\*(ID|Fecha|Tipo|Área|Area):\*\*", re.M)
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


IMG = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}


def docx_text(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    body = root.find(W + "body")
    out, ntab = [], 0
    for el in list(body if body is not None else root):
        if el.tag == W + "p":
            txt = "".join(t.text or "" for t in el.iter(W + "t")).strip()
            if txt:
                out.append(txt)
        elif el.tag == W + "tbl":
            ntab += 1
            rows = [["".join(t.text or "" for t in tc.iter(W + "t")).strip() for tc in tr.iter(W + "tc")]
                    for tr in el.iter(W + "tr")]
            from .tables import to_text
            try:
                out.append(to_text([(f"tabla {ntab} del documento", rows)], "documento Word"))
            except ValueError:
                pass
    return "\n\n".join(out)


def media_type(filename: str):
    f = filename.lower()
    if f.endswith(".pdf"):
        return "application/pdf"
    return next((v for k, v in IMG.items() if f.endswith(k)), None)


def raw_text(filename: str, data: bytes | str, transcribe=None) -> str:
    """transcribe(data, media_type, filename) -> str  (Claude) para imágenes y PDF."""
    if isinstance(data, str):
        return data
    from .tables import is_table, table_text
    f = filename.lower()
    if f.endswith(".docx"):
        return docx_text(data)
    if is_table(f):
        return table_text(filename, data)
    mt = media_type(f)
    if mt:
        if not transcribe:
            raise ValueError("Para leer imágenes o PDF se necesita Claude (configura la API key en ⋯ → Conectar Claude)")
        return transcribe(data, mt, filename)
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("No se pudo decodificar el archivo")


def to_markdown(text: str, meta: dict, next_id: str, filename: str = "") -> str:
    """El encabezado estándar del texto/archivo tiene prioridad; los campos del formulario completan lo faltante."""
    text = text.replace("\r\n", "\n").strip()
    found = dict(re.findall(r"^\*\*(ID|Fecha|Tipo|Área|Area):\*\*\s*(.+?)\s*$", text, re.M))
    found = {k.replace("Area", "Área"): v for k, v in found.items()}
    m = re.search(r"^#\s+(.+)$", text, re.M)
    body = "\n".join(l for l in text.splitlines() if not l.startswith("# ") and not HDR.match(l)).strip()
    stem = re.sub(r"[_-]+", " ", re.sub(r"\.\w+$", "", filename)).strip()
    f = {
        # el encabezado del archivo manda; el formulario completa lo que falte
        "ID": (found.get("ID") or meta.get("id") or next_id).strip().upper(),
        "Fecha": found.get("Fecha") or meta.get("fecha") or date.today().isoformat(),
        "Tipo": found.get("Tipo") or meta.get("tipo") or "Documento",
        "Área": found.get("Área") or meta.get("area") or "Sin área",
    }
    titulo = (m.group(1).strip() if m else "") or meta.get("titulo") or stem or "Fuente incorporada"
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", f["Fecha"]):
        raise ValueError(f"Fecha inválida '{f['Fecha']}' (usa AAAA-MM-DD)")
    if not body:
        raise ValueError("La fuente no tiene contenido")
    hdr = "\n".join(f"**{k}:** {v}" for k, v in f.items())
    return f"# {titulo}\n\n{hdr}\n\n{body}\n"
