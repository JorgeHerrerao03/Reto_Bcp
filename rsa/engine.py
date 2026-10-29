"""Motor con estado versionado: run(), incorporar(doc), preview(doc), deshacer(), sync(dir) y diff."""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from . import brief, llm, strategy
from .analyze import analyze
from .brain import Brain
from .convert import raw_text, to_markdown
from .corpus import load_package, parse_md
from .tools import make_runner

# En un .exe (PyInstaller) los datos viven junto al ejecutable, no en el bundle temporal
ID_RE = re.compile(r"F\d{2,4}")
AGENT_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]


def default_paquete() -> Path:
    for c in (AGENT_DIR / "paquete", AGENT_DIR.parent / "Revenue_Signals_Paquete_Candidatos_v3", AGENT_DIR.parent / "paquete"):
        if (c / "indice_fuentes.csv").exists():
            return c
    raise FileNotFoundError("No se encontró el paquete; usa --paquete RUTA")


def _table_stats_from_rows(txt: str) -> str:
    """Si la transcripción trae filas 'Fila n · col: val | ...', se recalculan las estadísticas con código."""
    import re as _re
    from .tables import stats
    rows = [l for l in txt.splitlines() if _re.match(r"\s*Fila \d+ ·", l)]
    if len(rows) < 2:
        return txt
    recs = [dict(kv.split(":", 1) for kv in l.split("·", 1)[1].split("|") if ":" in kv) for l in rows]
    header = list(dict.fromkeys(k.strip() for r in recs for k in r))
    grid = [[next((v.strip() for k, v in r.items() if k.strip() == h), "") for h in header] for r in recs]
    calc = stats(header, grid)
    return "\n".join(calc + [txt]) if calc else txt


def _jac(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a | b else 0


def _status(c):
    return c.get("superada") or c["tipo"]


class Engine:
    def __init__(self, paquete=None, out=None, use_llm=False, solo_reglas=False):
        self.solo_reglas = solo_reglas or os.getenv("RSA_MODO", "").lower() == "reglas"
        self.paquete = Path(paquete) if paquete else default_paquete()
        self.out = Path(out) if out else AGENT_DIR / "out"
        self.inc_dir = self.out / "incorporadas"
        self.state_f = self.out / "state.json"
        self.use_llm = use_llm
        self.out.mkdir(parents=True, exist_ok=True)
        self.state = json.loads(self.state_f.read_text(encoding="utf-8")) if self.state_f.exists() else {}
        if self.state and "incorporadas" not in self.state:  # estado de una versión anterior → empezar limpio
            self.state = {}
        self.state.setdefault("versiones", [])
        self.state.setdefault("incorporadas", [])

    # ---------- fuentes ----------
    def reset(self):
        shutil.rmtree(self.out, ignore_errors=True)
        self.__init__(self.paquete, self.out, self.use_llm, self.solo_reglas)
        self.state = {"versiones": [], "incorporadas": []}  # por si el FS no permitió borrar

    def sources(self, extra=None):
        srcs = load_package(self.paquete)
        for sid in self.state["incorporadas"]:
            srcs.append(parse_md(self._inc_path(sid), origen="incorporada"))
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
        meta = dict(meta or {})
        ai = self.brain()

        def transcribe(raw, mt, fname):
            if not ai:
                raise ValueError("Para leer imágenes o PDF se necesita Claude (⋯ → Conectar Claude)")
            titulo, txt = ai.transcribe(raw, mt, fname)
            if titulo and not meta.get("titulo"):
                meta["titulo"] = titulo
            txt = _table_stats_from_rows(txt)
            kind = "PDF" if mt == "application/pdf" else "imagen"
            return f"Contenido transcrito por Claude desde {kind} '{fname}'; verificar contra el original antes de actuar.\n{txt}"

        return to_markdown(raw_text(filename, data, transcribe), meta, self.next_id(), filename)

    def _parse_text(self, md):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "nueva.md"
            p.write_text(md, encoding="utf-8")
            s = parse_md(p, origen="incorporada")
        return s

    def _validate(self, src):
        if not ID_RE.fullmatch(src.id):
            raise ValueError(f"ID inválido '{src.id}': usa F seguido de dígitos (p.ej. F19)")
        if src.id in {s.id for s in self.sources()}:
            raise ValueError(f"ID duplicado: {src.id}")

    def free_id(self, md):
        """Si el ID del encabezado está ocupado o es inválido, lo reemplaza por el siguiente libre."""
        sid = self._parse_text(md).id
        if ID_RE.fullmatch(sid) and sid not in {s.id for s in self.sources()}:
            return md
        return re.sub(r"^\*\*ID:\*\*.*$", f"**ID:** {self.next_id()}", md, count=1, flags=re.M)

    def _inc_path(self, sid):
        p = (self.inc_dir / f"{sid}.md").resolve()
        if not ID_RE.fullmatch(sid) or p.parent != self.inc_dir.resolve():
            raise ValueError(f"ID inválido '{sid}'")
        return p

    # ---------- ciclo ----------
    def brain(self):
        """Claude decide siempre que haya API key; RSA_MODO=reglas o --solo-reglas fuerza modo determinístico."""
        if self.solo_reglas or not llm.cfg()["key"]:
            return None
        return Brain(AGENT_DIR / ".cache" / "claude_cache.json")

    def motor_mode(self):
        return "reglas" if self.solo_reglas or not llm.cfg()["key"] else "claude"

    def _analyze(self, srcs, evento):
        by_id = {s.id: s for s in srcs}
        log = [{"accion": "ingestar", "n_fuentes": len(srcs), "fuentes": [f"{s.id}:{s.sha1}" for s in srcs]}]
        ai = self.brain()
        res = analyze(srcs, tool_runner=make_runner(self.paquete / "herramientas" / "consultar_parametros.py"), log=log,
                      ai=ai)
        if ai and res["motor"]["modo"] == "claude":
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(4) as ex:
                for s, r in zip(res["signals"], ex.map(ai.summary, res["signals"])):
                    s["resumen_llm"] = r
            fx = {s.id: {"area": s.area, "titulo": s.titulo, "origen": s.origen} for s in srcs}
            with ThreadPoolExecutor(4) as ex:
                for s, b in zip(res["signals"], ex.map(lambda x: strategy.build(x, fx, ai), res["signals"])):
                    s["brief"] = b
            ai.save()
            res["log"].extend(ai.events)
            ai.events = []
            res["motor"] = ai.motor()
        elif ai:
            err = next((e.get("error") for e in res["log"] + ai.events if "fallo" in e.get("accion", "")), "")
            res["motor"] = {**ai.motor(), "modo_solicitado": "claude",
                            "aviso": "Claude no respondió; se usó el motor de reglas" + (f" · {err[:220]}" if err else "")}
            res["log"].extend(ai.events)
            ai.events = []
            res["motor"]["modo"] = "reglas"
        fx = {s.id: {"area": s.area, "titulo": s.titulo, "origen": s.origen} for s in srcs}
        for s in res["signals"]:
            s.setdefault("brief", strategy.fallback(s, fx))
        self._assign_ids(res["signals"])
        prev = self.state["versiones"][-1] if self.state["versiones"] else None
        ver = {"v": len(self.state["versiones"]) + 1, "ts": datetime.now().isoformat(timespec="seconds"),
               "evento": evento, "fuentes": [s.to_dict() for s in srcs], **res,
               "incorporadas": [s.id for s in srcs if s.origen == "incorporada"]}
        ver["diff"] = diff(prev, ver) if prev else None
        return ver, by_id

    def run(self, evento=None):
        evento = evento or ("re-ejecución" if self.state["versiones"] else "ingesta inicial")
        ver, by_id = self._analyze(self.sources(), evento)
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
               "descartada": next((d for d in ver["descartadas"] if d["fuente"] == src.id), None),
               "comites": ver["comites"], "motor": ver["motor"],
               "auditoria_relevancia": [a for a in ver["auditoria_relevancia"] if a["fuente"] == src.id]}
        return out

    def incorporar(self, path=None, md=None):
        md = md or self.build_md(path=path)
        src = self._parse_text(md)
        self._validate(src)
        if not self.state["versiones"]:
            self.run()
        self.inc_dir.mkdir(parents=True, exist_ok=True)
        self._inc_path(src.id).write_text(md, encoding="utf-8")
        self.state["incorporadas"].append(src.id)
        try:
            return self.run(evento=f"incorporar {src.id} · {src.titulo}")
        except Exception:
            self.state["incorporadas"].remove(src.id)  # transaccional: si el análisis falla, no queda a medias
            raise

    @staticmethod
    def _inc_of(ver):
        return ver.get("incorporadas", [f["id"] for f in ver["fuentes"] if f.get("origen") == "incorporada"])

    def deshacer(self):
        """Retira la última fuente incorporada y vuelve a la última versión que NO la contiene
        (también descarta re-análisis posteriores a esa incorporación)."""
        if not self.state["incorporadas"]:
            raise ValueError("No hay incorporaciones que deshacer")
        sid = self.state["incorporadas"][-1]
        keep = [v for v in self.state["versiones"] if sid not in self._inc_of(v)]
        target = keep[-1] if keep else None
        if not target or set(self._inc_of(target)) != set(self.state["incorporadas"][:-1]):
            raise ValueError(f"No hay una versión guardada sin {sid}; usa Reset para reconstruir")
        n_drop = len(self.state["versiones"]) - (self.state["versiones"].index(target) + 1)
        self.state["incorporadas"].pop()
        del self.state["versiones"][len(self.state["versiones"]) - n_drop:]
        self._write(target, {s.id: s for s in self.sources()})
        return sid

    def sync(self, folder):
        """Re-construye todo desde cero e incorpora cada .md de la carpeta en orden de fecha (usado por CI)."""
        self.reset()
        self.run()
        files = []
        for p in sorted(Path(folder).glob("*.md")):
            if p.name.lower() == "readme.md":
                continue
            try:
                files.append((self._parse_text(self.build_md(path=p)).fecha, p.name, p))
            except ValueError as e:
                print(f"[sync][omitido] {p.name}: {e}")
        for _, name, p in sorted(files):
            try:  # el ID se asigna al incorporar cada archivo: dos archivos sin ID reciben F19 y F20
                self.incorporar(md=self.free_id(self.build_md(path=p)))
                print(f"[sync] incorporado {name}")
            except ValueError as e:
                print(f"[sync][omitido] {name}: {e}")
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
        fx = {f["id"]: {"area": f["area"], "titulo": f["titulo"], "origen": f.get("origen")} for f in ver["fuentes"]}
        for s in ver["signals"]:
            if s.get("brief"):
                s["brief"] = strategy.apply_cambios(s["brief"], s, fx)
            md = brief.render(s, by_id)
            if s.get("resumen_llm"):
                md = md.replace("## Tesis", f"## Síntesis de la evidencia (Claude, citas validadas)\n{s['resumen_llm']}\n\n## Tesis", 1)
            (bd / f"{s['id']}_brief.md").write_text(md, encoding="utf-8")
            (bd / f"{s['id']}_traza.md").write_text(brief.trace(s, ver["log"]), encoding="utf-8")
            try:
                (bd / f"{s['id']}_brief.docx").write_bytes(self.docx(s["id"], ver))
            except OSError:
                pass
        self.save()
        report.write(self.state, self.out / "reporte.html")

    def ensure_briefs(self, ver=None, save=True):
        """Completa el brief estratégico en versiones guardadas sin él (p.ej. creadas con una versión anterior)."""
        ver = ver or self.latest()
        missing = [s for s in ver["signals"] if not s.get("brief")]
        if not missing:
            return 0
        fx = {f["id"]: {"area": f["area"], "titulo": f["titulo"], "origen": f.get("origen")} for f in ver["fuentes"]}
        ai = self.brain() if (ver.get("motor") or {}).get("modo") == "claude" else None
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=4) as ex:
            for s, b in zip(missing, ex.map(lambda x: strategy.build(x, fx, ai), missing)):
                s["brief"] = b
        if ai:
            ai.save()
        if save:
            self.save()
        return len(missing)

    def docx(self, sid, ver=None):
        from . import docx
        ver = ver or self.latest()
        self.ensure_briefs(ver)
        s = next(x for x in ver["signals"] if x["id"] == sid)
        s = {**s, "recomendacion": brief.recomendacion(s)}
        fx = {f["id"]: {"area": f["area"], "titulo": f["titulo"], "origen": f.get("origen")} for f in ver["fuentes"]}
        s["brief"] = strategy.apply_cambios(dict(s.get("brief") or {}), s, fx)
        logo_f = AGENT_DIR / "marca" / "logo.png"
        return docx.build(s, {f["id"]: f for f in ver["fuentes"]}, ver, logo_f.read_bytes() if logo_f.exists() else None)

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
            filas = [n for n in nuevos if n["texto"].startswith("Fila ") and " · " in n["texto"][:12]]
            for n in [n for n in nuevos if n not in filas]:
                lim = 300 if n["texto"].startswith("Cálculo") else 110
                out["explicacion"].append(f"  + [{n['sid']}] {n['tipo']}: «{n['texto'][:lim]}»")
            if filas:
                out["explicacion"].append(f"  + {len(filas)} filas de tabla como evidencia citable "
                                          f"([{filas[0]['sid']}] … [{filas[-1]['sid']}])")
    return out
