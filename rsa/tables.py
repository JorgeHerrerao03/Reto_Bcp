"""Datos tabulares (.xlsx / .csv / .tsv / tablas de Word) → fuente citable.
Cada fila es una oración (`Fxx.n`) y los cálculos los hace el CÓDIGO, nunca el LLM: Claude solo interpreta
resultados ya calculados, así cualquier cifra del brief es verificable."""
from __future__ import annotations

import csv
import io
import re
import statistics
import zipfile
from datetime import date, timedelta
from xml.etree import ElementTree as ET

MAX_ROWS = 200
S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


# ---------- lectura ----------
def _col_idx(ref):
    letters = re.match(r"[A-Z]+", ref).group(0)
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def read_xlsx(data: bytes):
    z = zipfile.ZipFile(io.BytesIO(data))
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(S + "si"):
            shared.append("".join(t.text or "" for t in si.iter(S + "t")))
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    sheets = []
    for sh in wb.iter(S + "sheet"):
        target = rels.get(sh.get(RID), "")
        path = "xl/" + target.lstrip("/").replace("xl/", "") if not target.startswith("/xl/") else target[1:]
        if path not in z.namelist():
            continue
        grid = []
        for row in ET.fromstring(z.read(path)).iter(S + "row"):
            vals = {}
            for c in row.iter(S + "c"):
                t, v = c.get("t"), c.find(S + "v")
                if t == "s" and v is not None:
                    val = shared[int(v.text)]
                elif t == "inlineStr":
                    val = "".join(x.text or "" for x in c.iter(S + "t"))
                elif t == "b" and v is not None:
                    val = "VERDADERO" if v.text == "1" else "FALSO"
                else:
                    val = v.text if v is not None else ""
                vals[_col_idx(c.get("r"))] = val
            if vals:
                grid.append([vals.get(i, "") for i in range(max(vals) + 1)])
        sheets.append((sh.get("name"), grid))
    return sheets


def read_csv(data: bytes | str, filename=""):
    txt = data if isinstance(data, str) else None
    if txt is None:
        for enc in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                txt = data.decode(enc)
                break
            except UnicodeDecodeError:
                continue
    try:
        dialect = csv.Sniffer().sniff(txt[:4000], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel_tab if filename.lower().endswith(".tsv") else csv.excel
    return [(re.sub(r"\.\w+$", "", filename) or "tabla", [r for r in csv.reader(io.StringIO(txt), dialect)])]


# ---------- normalización ----------
def _num(v):
    if v is None:
        return None
    s = str(v).strip().replace("S/", "").replace("$", "").replace("%", "").replace(" ", "").strip()
    if not s:
        return None
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", s):      # 1.234,56
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d+,\d+", s):                      # 12,5
        s = s.replace(",", ".")
    else:
        s = s.replace(",", "")                               # 1,234.56
    try:
        return float(s)
    except ValueError:
        return None


def _fmt(x):
    if x and abs(x) < 1:
        return f"{x:.6f}".rstrip("0").rstrip(".")       # tasas pequeñas: no redondear a 0
    s = f"{x:,.2f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def _clean(sheets):
    out = []
    for name, grid in sheets:
        grid = [[str(c).strip() for c in r] for r in grid if any(str(c).strip() for c in r)]
        if len(grid) < 2:
            continue
        header = [h or f"col{i + 1}" for i, h in enumerate(grid[0])]
        rows = [r + [""] * (len(header) - len(r)) for r in grid[1:]]
        for i, h in enumerate(header):          # fechas seriales de Excel en columnas tipo fecha
            if re.search(r"fecha|date|periodo", h, re.I):
                for r in rows:
                    n = _num(r[i])
                    if n and 20000 < n < 80000 and float(n).is_integer():
                        r[i] = (date(1899, 12, 30) + timedelta(days=int(n))).isoformat()
        out.append((name, header, rows))
    return out


# ---------- cálculos determinísticos ----------
def stats(header, rows):
    cols = list(zip(*rows)) if rows else []
    num_cols, cat_cols = [], []
    for i, h in enumerate(header):
        vals = [v for v in cols[i] if v != ""]
        nums = [_num(v) for v in vals]
        if vals and sum(n is not None for n in nums) / len(vals) >= 0.8 and not re.search(r"\bid\b|codigo|código|ruc|dni", h, re.I):
            num_cols.append(i)
        elif vals and 1 < len(set(vals)) <= 12 and len(set(vals)) < len(vals):
            cat_cols.append(i)
    lines = []
    for i in num_cols[:4]:
        xs = [n for n in (_num(v) for v in cols[i]) if n is not None]
        if xs:
            lines.append(f"Cálculo (código) · {header[i]}: n {len(xs)}, total {_fmt(sum(xs))}, promedio {_fmt(statistics.mean(xs))}, "
                         f"mínimo {_fmt(min(xs))}, máximo {_fmt(max(xs))}")
    for g in cat_cols[:2]:
        groups = {}
        for r in rows:
            groups.setdefault(r[g], []).append(r)
        for i in num_cols[:3]:
            parts, means = [], {}
            for k, rs in sorted(groups.items()):
                xs = [n for n in (_num(r[i]) for r in rs) if n is not None]
                if xs:
                    means[k] = statistics.mean(xs)
                    parts.append(f"{k} {_fmt(means[k])} (n {len(xs)})")
            if len(means) >= 2:
                line = f"Cálculo (código) · {header[i]} promedio por {header[g]}: " + ", ".join(parts)
                if len(means) == 2:
                    (a, va), (b, vb) = sorted(means.items(), key=lambda kv: kv[1])   # a = menor, b = mayor
                    if vb:
                        line += (f" | {a}/{b} = {_fmt(va / vb)} ({a} equivale al {_fmt(va / vb * 100)}% de {b}); "
                                 f"diferencia {a} vs {b} {_fmt((va - vb) / vb * 100)}%")
                lines.append(line)
    return lines


def to_text(sheets, filename=""):
    """Texto de fuente: descripción, cálculos y una línea por fila (cada línea = una oración citable)."""
    out = []
    for name, header, rows in _clean(sheets):
        out.append(f"Tabla '{name}' del archivo {filename or 'adjunto'} con {len(rows)} filas y columnas: {', '.join(header)}")
        out += stats(header, rows)
        for n, r in enumerate(rows[:MAX_ROWS], 1):
            out.append(f"Fila {n} · " + " | ".join(f"{h}: {v}" for h, v in zip(header, r) if v != ""))
        if len(rows) > MAX_ROWS:
            out.append(f"Se omiten {len(rows) - MAX_ROWS} filas en el detalle; los cálculos usan todas las filas")
    if not out:
        raise ValueError("La tabla no tiene filas con datos")
    return "\n".join(out)


def is_table(filename):
    return filename.lower().endswith((".xlsx", ".xlsm", ".csv", ".tsv"))


def table_text(filename, data):
    f = filename.lower()
    sheets = read_xlsx(data) if f.endswith((".xlsx", ".xlsm")) else read_csv(data, filename)
    return to_text(sheets, filename)
