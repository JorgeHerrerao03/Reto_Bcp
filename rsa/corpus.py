"""Ingesta de fuentes: índice CSV + markdown. Nunca modifica los originales."""
from __future__ import annotations
import csv
import hashlib
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

from .text import sentences

HDR = re.compile(r"^\*\*(ID|Fecha|Tipo|Área|Area):\*\*\s*(.+?)\s*$", re.M)


@dataclass
class Source:
    id: str
    fecha: str
    tipo: str
    area: str
    titulo: str
    archivo: str
    body: str
    sha1: str
    origen: str = "paquete"          # paquete | incorporada
    sents: list = field(default_factory=list)

    def to_dict(self):
        d = asdict(self)
        d.pop("body")
        return d


def parse_md(path: Path, meta: dict | None = None, origen="paquete") -> Source:
    raw = path.read_text(encoding="utf-8-sig")
    hdr = {k.replace("Area", "Área"): v for k, v in HDR.findall(raw)}
    m = re.search(r"^#\s+(.+)$", raw, re.M)
    body = "\n".join(l for l in raw.splitlines() if not l.startswith("#") and not HDR.match(l)).strip()
    meta = meta or {}
    sid = meta.get("id") or hdr.get("ID") or path.stem
    src = Source(
        id=sid,
        fecha=meta.get("fecha") or hdr.get("Fecha", ""),
        tipo=meta.get("tipo") or hdr.get("Tipo", ""),
        area=meta.get("area") or hdr.get("Área", ""),
        titulo=meta.get("titulo") or (m.group(1).strip() if m else path.stem),
        archivo=str(path),
        body=body,
        sha1=hashlib.sha1(raw.encode()).hexdigest()[:10],
        origen=origen,
    )
    src.sents = [{"sid": f"{sid}.{i + 1}", "texto": s} for i, s in enumerate(sentences(body))]
    return src


def load_package(root: Path) -> list[Source]:
    root = Path(root)
    idx = root / "indice_fuentes.csv"
    out, warnings = [], []
    with idx.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            p = root / row["archivo"]
            if not p.exists():
                warnings.append(f"{row['id']}: archivo no encontrado {p}")
                continue
            s = parse_md(p, row)
            for k in ("fecha", "tipo", "area"):
                hk = {"area": "Área"}.get(k, k.capitalize())
                hv = dict((a.replace("Area", "Área"), b) for a, b in HDR.findall(p.read_text(encoding="utf-8-sig"))).get(hk)
                if hv and hv != row[k]:
                    warnings.append(f"{row['id']}: '{k}' índice={row[k]} archivo={hv}")
            out.append(s)
    for w in warnings:
        print("[ingesta][warn]", w)
    return out
