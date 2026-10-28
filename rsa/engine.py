"""Motor con estado versionado: run(), incorporar(doc), preview(doc), deshacer(), sync(dir) y diff."""
from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from . import brief, llm
from .analyze import analyze
from .convert import raw_text, to_markdown
from .corpus import load_package, parse_md
from .tools import make_runner

# En un .exe (PyInstaller) los datos viven junto al ejecutable, no en el bundle temporal
AGENT_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]


def default_paquete() -> Path:
    for c in (AGENT_DIR / "paquete", AGENT_DIR.parent / "Revenue_Signals_Paquete_Candidatos_v3", AGENT_DIR.parent / "paquete"):
        if (c / "indice_fuentes.csv").exists():
            return c
    raise FileNotFoundError("No se encontró el paquete; usa --paquete RUTA")


def _jac(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a | b else 0


def _status(c):
    return c.get("superada") or c["tipo"]


class Engine:
    def __init__(self, paquete=None, out=None, use_llm=False):
        self.paquete = Path(paquete) if paquete else default_paquete()
        self.out = Path(out) if out else AGENT_DIR / "out"
        self.inc_dir = self.out / "incorporadas"
        self.state_f = self.out / "state.json"
        self.use_llm = use_llm
        self.out.mkdir(parents=True, exist_ok=True)
        self.state = json.loads(self.state_f.read_text(encoding="utf-8")) if self.state_f.exists() else {}
        self.state.setdefault("versiones", [])
        self.state.setdefault("incorporadas", [])

    # ---------- fuentes ----------
    def reset(self):
        shutil.rmtree(self.out, ignore_errors=True)
        self.__init__(self.paquete, self.out, self.use_llm)
        self.state = {"versiones": [], "incorporadas": []}  # por si el FS no permitió borrar

    def sources(self, extra=None):
        srcs = load_package(self.paquete)
        for sid in self.state["incorporadas"]:
            srcs.append(parse_md(self.inc_dir / f"{sid}.md", origen="incorporada"))
        if extra:
            srcs.append(extra)
        return srcs

    def next_id(self):
        n = max(int(m.group(1)) for s in self.sources() if (m := re.match(r"F(\d+)$", s.id))) + 1
        return f"F{n:02d}"

    def build_md(self, data=None, filename="", meta=None, path=None):
        if path:
            path = Path(path)
            data, filename = path.read_bytes(), path.name
        return to_markdown(raw_text(filename, data), meta or {}, self.next_id(), filename)

    def _parse_text(self, md):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "nueva.md"
            p.write_text(md, encoding="utf-8")
            s = parse_md(p, origen="incorporada")
        return s

    def _validate(self, src):
        if src.id in {s.id for s in self.sources()}:
            raise ValueError(f"ID duplicado: {src.id}")

    # ---------- ciclo ----------
    def _analyze(self, srcs, evento):
        by_id = {s.id: s for s in srcs}
        log = [{"accion": "ingestar", "n_fuentes": len(srcs), "fuentes": [f"{s.id}:{s.sha1}" for s in srcs]}]
        res = analyze(srcs, tool_runner=make_runner(self.paquete / "herramientas" / "consultar_parametros.py"), log=log)
        self._assign_ids(res["signals"])
        prev = self.state["versiones"][-1] if self.state["versiones"] else None
        ver = {"v": len(self.state["versiones"]) + 1, "ts": datetime.now().isoformat(timespec="seconds"),
               "evento": evento, "fuentes": [s.to_dict() for s in srcs], **res}
        ver["diff"] = diff(prev, ver) if prev else None
        return ver, by_id

    def run(self, evento=None):
        evento = evento or ("re-ejecución" if self.state["versiones"] else "ingesta inicial")
        ver, by_id = self._analyze(self.sources(), evento)
        if self.use_llm:
            for s in ver["signals"]:
                s["resumen_llm"] = llm.summarize(s, ver["log"])
        self.state["versiones"].append(ver)
        self._write(ver, by_id)
        return ver

    def preview(self, md):
        """Qué pasaría si incorporo esta fuente: análisis completo sin persistir nada."""
        src = self._parse_text(md)
        self._validate(src)
        if not self.state["versiones"]:
            self.run()
        ver, _ = self._analyze(self.sources(extra=src), f"preview {src.id}")
        out = {"fuente": src.to_dict(), "markdown": md, "diff": ver["diff"],
               "ranking": [{"id": s["id"], "titulo": s["titulo"], "score": s["score"]} for s in ver["signals"]],
               "clasificacion": [c for s in ver["signals"] for c in s["claims"] if c["fuente"] == src.id],
               "descartada": next((d for d in ver["descartadas"] if d["fuente"] == src.id), None)}
        if self.use_llm:
            out["revision_llm"] = llm.review_new_doc(src, ver["signals"], ver["log"])
        return out

    def incorporar(self, path=None, md=None):
        md = md or self.build_md(path=path)
        src = self._parse_text(md)
        self._validate(src)
        if not self.state["versiones"]:
            self.run()
        self.inc_dir.mkdir(parents=True, exist_ok=True)
        (self.inc_dir / f"{src.id}.md").write_text(md, encoding="utf-8")
        self.state["incorporadas"].append(src.id)
        return self.run(evento=f"incorporar {src.id} · {src.titulo}")

    def deshacer(self):
        if len(self.state["versiones"]) < 2 or not self.state["incorporadas"]:
            raise ValueError("No hay incorporaciones que deshacer")
        sid = self.state["incorporadas"].pop()
        self.state["versiones"].pop()
        ver = self.state["versiones"][-1]
        self._write(ver, {s.id: s for s in self.sources()})
        return sid

    def sync(self, folder):
        """Re-construye todo desde cero e incorpora cada .md de la carpeta en orden de fecha (usado por CI)."""
        use_llm, self.use_llm = self.use_llm, False  # Claude solo sobre la versión final (costo mínimo)
        self.reset()
        self.run()
        files = []
        for p in sorted(Path(folder).glob("*.md")):
            if p.name.lower() == "readme.md":
                continue
            try:
                md = self.build_md(path=p)
                files.append((self._parse_text(md).fecha, p.name, md))
            except ValueError as e:
                print(f"[sync][omitido] {p.name}: {e}")
        for _, name, md in sorted(files):
            try:
                self.incorporar(md=md)
                print(f"[sync] incorporado {name}")
            except ValueError as e:
                print(f"[sync][omitido] {name}: {e}")
        self.use_llm = use_llm
        if use_llm:
            ver = self.latest()
            for s in ver["signals"]:
                s["resumen_llm"] = llm.summarize(s, ver["log"])
            self._write(ver, {s.id: s for s in self.sources()})
        return self.latest()

    # ---------- IDs estables entre versiones ----------
    def _assign_ids(self, signals):
        prev = self.state["versiones"][-1]["signals"] if self.state["versiones"] else []
        used, nxt = set(), max([int(s["id"][1:]) for s in prev] or [0]) + 1
        for s in signals:
            best = max(((_jac(s["fuentes"], p["fuentes"]), p["id"]) for p in prev if p["id"] not in used),
                       default=(0, None))
            if best[0] >= 0.4:
                s["id"] = best[1]
            else:
                s["id"] = f"S{nxt}"
                nxt += 1
            used.add(s["id"])

    # ---------- salidas ----------
    def _write(self, ver, by_id):
        from . import report
        bd = self.out / "briefs"
        bd.mkdir(exist_ok=True)
        for f in bd.glob("*.md"):
            try:
                f.unlink()
            except OSError:
                pass
        for s in ver["signals"]:
            md = brief.render(s, by_id)
            if s.get("resumen_llm"):
                md = md.replace("## Tesis", f"## Resumen (Claude, citas validadas)\n{s['resumen_llm']}\n\n## Tesis", 1)
            (bd / f"{s['id']}_brief.md").write_text(md, encoding="utf-8")
            (bd / f"{s['id']}_traza.md").write_text(brief.trace(s, ver["log"]), encoding="utf-8")
        self.save()
        report.write(self.state, self.out / "reporte.html")

    def save(self):
        self.state_f.write_text(json.dumps(self.state, ensure_ascii=False, indent=1), encoding="utf-8")

    def latest(self):
        return self.state["versiones"][-1]


# ---------- diff ----------
def diff(prev, cur) -> dict:
    P = {s["id"]: s for s in prev["signals"]}
    C = {s["id"]: s for s in cur["signals"]}
    rp = {s["id"]: i + 1 for i, s in enumerate(prev["signals"])}
    rc = {s["id"]: i + 1 for i, s in enumerate(cur["signals"])}
    out = {"nuevas": [k for k in C if k not in P], "eliminadas": [k for k in P if k not in C], "cambios": {},
           "fuentes_nuevas": sorted({f["id"] for f in cur["fuentes"]} - {f["id"] for f in prev["fuentes"]}),
           "descartadas_nuevas": sorted({d["fuente"] for d in cur["descartadas"]} -
                                        {d["fuente"] for d in prev["descartadas"]}),
           "explicacion": []}
    for k in out["descartadas_nuevas"]:
        d = next(x for x in cur["descartadas"] if x["fuente"] == k)
        out["explicacion"].append(f"{k} descartada como ruido: {d['motivo']}" + (f" («{d['evidencia']}»)" if d[
            'evidencia'] else ""))
    for k in out["nuevas"]:
        out["explicacion"].append(f"Nueva señal {k}: {C[k]['titulo']} ({', '.join(C[k]['fuentes'])})")
    for k in set(P) & set(C):
        a, b = P[k], C[k]
        sa = {c["sid"]: _status(c) for c in a["claims"]}
        trans = [{"sid": c["sid"], "de": sa[c["sid"]], "a": _status(c), "por": c.get("por"), "texto": c["texto"]}
                 for c in b["claims"] if c["sid"] in sa and sa[c["sid"]] != _status(c)]
        nuevos = [{"sid": c["sid"], "tipo": c["tipo"], "texto": c["texto"]} for c in b["claims"] if c["sid"] not in sa]
        ch = {"score": [a["score"], b["score"]], "rank": [rp[k], rc[k]],
              "componentes": [a["componentes"], b["componentes"]],
              "confianza": [a["confianza"], b["confianza"]],
              "recomendacion": [brief.recomendacion(a), brief.recomendacion(b)],
              "fuentes_nuevas": sorted(set(b["fuentes"]) - set(a["fuentes"])),
              "transiciones": trans, "claims_nuevos": nuevos,
              "no_afirmo": [sorted(set(b["no_afirmo"]) - set(a["no_afirmo"])),
                            sorted(set(a["no_afirmo"]) - set(b["no_afirmo"]))]}
        if any([abs(b["score"] - a["score"]) >= 0.1, trans, nuevos, ch["fuentes_nuevas"]]):
            out["cambios"][k] = ch
            d = round(b["score"] - a["score"], 1)
            out["explicacion"].append(f"{k} ({b['titulo']}): score {a['score']} → {b['score']} ({d:+}), "
                                      f"rank {rp[k]} → {rc[k]}" + (f"; nuevas fuentes {', '.join(ch['fuentes_nuevas'])}"
                                                                    if ch['fuentes_nuevas'] else ""))
            for t in trans:
                out["explicacion"].append(f"  [{t['sid']}] {t['de']} → {t['a']}" + (f" por [{t['por']}]" if t["por"]
                                                                                    else ""))
            for n in nuevos:
                out["explicacion"].append(f"  + [{n['sid']}] {n['tipo']}: «{n['texto'][:110]}»")
    return out
