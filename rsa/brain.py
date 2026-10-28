"""Motor Claude-first. Claude interpreta (español informal, spanglish, inglés); las reglas auditan.

Llamadas (todas JSON, validadas y cacheadas por contenido):
  1. fuente      → relevancia, palanca, tipo de cada oración, entidades para la herramienta
  2. relaciones  → por señal: qué afirmación posterior refuta / resuelve / confirma a cuál anterior
  3. comité      → solo si Claude y reglas discrepan: postura A ∥ postura B → juez decide
  4. resumen     → resumen ejecutivo por señal (citas validadas en llm.summarize)
Si cualquier llamada falla o no valida → ese paso cae a reglas y queda registrado."""
from __future__ import annotations

import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import lexicon as L
from . import llm

PROMPT_VER = "v1"
TIPOS = {"hecho", "hipotesis", "faltante", "correccion", "advertencia"}
RELS = {"refuta", "resuelve", "confirma"}
PALANCAS = [p for p, _ in L.PALANCAS]

SYS = ("Eres analista senior de Revenue Optimization en un banco peruano. Lees documentos internos que pueden estar "
       "en español formal o informal, spanglish o inglés. Respondes SOLO con JSON válido, sin texto adicional. "
       "Nunca inventas datos, cifras ni IDs: solo usas los IDs entregados.")

DEF_TIPOS = ("hecho = afirmación verificable, dato observado o regla/política vigente; "
             "hipotesis = sospecha, interpretación, propuesta, plan o expectativa no confirmada; "
             "faltante = dato, confirmación, evidencia o acción pendiente (incluye solicitudes: 'se solicita', 'pending', 'TBD'); "
             "correccion = rectifica, aclara o desmiente algo dicho antes; "
             "advertencia = cautela metodológica sobre cómo interpretar la evidencia.")


def _h(x) -> str:
    return hashlib.sha1(json.dumps(x, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]


def _parse(txt):
    return json.loads(txt[txt.index("{"): txt.rindex("}") + 1])


class Brain:
    def __init__(self, cache_file: Path):
        self.cache_file = Path(cache_file)
        self.lock = threading.Lock()
        try:
            self.cache = json.loads(self.cache_file.read_text(encoding="utf-8"))
        except Exception:
            self.cache = {}
        self.model = llm.cfg()["model"]
        self.stats = {"llamadas": 0, "cache": 0, "costo_usd": 0.0, "fallos": 0, "comites": 0}
        self.events = []  # registro observable de cada llamada

    # ---------- infraestructura ----------
    def save(self):
        with self.lock:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_text(json.dumps(self.cache, ensure_ascii=False), encoding="utf-8")

    def _call(self, kind, key, prompt, max_tokens, label):
        ck = f"{kind}:{PROMPT_VER}:{self.model}:{_h(key)}"
        with self.lock:
            if ck in self.cache:
                self.stats["cache"] += 1
                self.events.append({"accion": f"claude_{kind}", "objeto": label, "cache": True})
                return self.cache[ck]
        try:
            txt, meta = llm.call(prompt, max_tokens, SYS, temperature=0)
            data = _parse(txt)
        except Exception as e:
            with self.lock:
                self.stats["fallos"] += 1
                self.events.append({"accion": f"claude_{kind}_fallo", "objeto": label, "error": str(e)[:160]})
            return None
        with self.lock:
            self.stats["llamadas"] += 1
            self.stats["costo_usd"] += meta["costo_usd"]
            self.events.append({"accion": f"claude_{kind}", "objeto": label, "cache": False, "ms": meta["ms"],
                                "tokens": meta["tokens"], "costo_usd": meta["costo_usd"]})
            self.cache[ck] = data
        return data

    # ---------- 1. fuente ----------
    def _source_prompt(self, s):
        sents = "\n".join(f"{x['sid']} | {x['texto']}" for x in s.sents)
        return (f"Fuente {s.id} · {s.fecha} · {s.tipo} · {s.area}\nTítulo: {s.titulo}\nOraciones (sid | texto):\n{sents}\n\n"
                f"Palancas económicas conocidas: {json.dumps(PALANCAS, ensure_ascii=False)}\n"
                f"Definiciones de tipo: {DEF_TIPOS}\n"
                "Relevante = tiene vínculo con ingresos, cobros, tarifas, precios, comisiones, costos, condiciones "
                "comerciales o productos financieros. Es ruido si declara no tener ese vínculo o trata solo temas internos "
                "(marca, infraestructura, bienestar, dashboards).\n"
                "Devuelve JSON:\n"
                '{"relevante": true|false, "motivo_ruido": "texto corto o null", "sid_ruido": "sid que lo prueba o null",'
                ' "palanca": "una de las conocidas, o \'nueva: <nombre corto en español>\', o null",'
                ' "operacional": true si describe algo que ya ocurre en producción/transacciones reales,'
                ' "producto": "nombre del producto o null", "canal": "Web|Sucursal|App|null", '
                '"parametro": "rate_input|selector_dia_pago|exoneracion_membresia|null",'
                ' "terminos": ["5 a 8 términos clave en español (traduce si viene en inglés)"],'
                ' "oraciones": [{"sid": "...", "tipo": "hecho|hipotesis|faltante|correccion|advertencia",'
                ' "accion": true si pide una acción o verificación, "razon": "máx. 12 palabras"}]}')

    def source(self, s):
        key = {"id": s.id, "sha": s.sha1, "sents": [x["texto"] for x in s.sents], "meta": [s.fecha, s.tipo, s.area]}
        d = self._call("fuente", key, self._source_prompt(s), 1500, s.id)
        if not isinstance(d, dict):
            return None
        valid = {x["sid"] for x in s.sents}
        ora = {}
        for o in d.get("oraciones") or []:
            if isinstance(o, dict) and o.get("sid") in valid and o.get("tipo") in TIPOS:
                ora[o["sid"]] = {"tipo": o["tipo"], "accion": bool(o.get("accion")), "razon": str(o.get("razon", ""))[:120]}
        p = d.get("palanca")
        if isinstance(p, str) and p.strip():
            p = p.strip()
            p = p if p in PALANCAS else (p.split(":", 1)[1].strip().capitalize() if p.lower().startswith("nueva")
                                         and ":" in p else None)
        else:
            p = None
        sid_r = d.get("sid_ruido") if d.get("sid_ruido") in valid else None
        return {"relevante": bool(d.get("relevante", True)), "motivo_ruido": d.get("motivo_ruido") or "",
                "sid_ruido": sid_r, "palanca": p, "operacional": bool(d.get("operacional")),
                "producto": d.get("producto"), "canal": d.get("canal"), "parametro": d.get("parametro"),
                "terminos": [str(t) for t in (d.get("terminos") or [])][:8], "oraciones": ora}

    def prefetch(self, sources, workers=6):
        with ThreadPoolExecutor(workers) as ex:
            res = dict(zip([s.id for s in sources], ex.map(self.source, sources)))
        self.save()
        return res

    # ---------- 2. relaciones ----------
    def relations(self, titulo, claims):
        rows = "\n".join(f"{c['sid']} | {c['fecha']} | {c['tipo']} | {c['texto']}" for c in claims)
        prompt = (f"Señal: {titulo}\nAfirmaciones ordenadas por fecha (sid | fecha | tipo | texto):\n{rows}\n\n"
                  "Identifica SOLO relaciones claras en que una afirmación POSTERIOR de OTRA fuente cambia el estado "
                  "de una ANTERIOR:\n- refuta: la contradice o desmiente (la anterior deja de ser válida)\n"
                  "- resuelve: responde o cierra un faltante anterior\n"
                  "- confirma: aporta evidencia que respalda una hipótesis anterior sin cerrarla\n"
                  "Además hasta 3 'cautelas': conclusiones que NO deben afirmarse con esta evidencia.\n"
                  'JSON: {"relaciones":[{"de":"sid","a":"sid","relacion":"refuta|resuelve|confirma",'
                  '"motivo":"máx. 15 palabras"}],"cautelas":["..."]}')
        key = [(c["sid"], c["fecha"], c["tipo"], c["texto"]) for c in claims]
        d = self._call("relaciones", key, prompt, 1200, titulo)
        if not isinstance(d, dict):
            return None
        by = {c["sid"]: c for c in claims}
        out = []
        for r in d.get("relaciones") or []:
            if not isinstance(r, dict):
                continue
            a, b, rel = by.get(r.get("a")), by.get(r.get("de")), r.get("relacion")
            if a and b and rel in RELS and a["fuente"] != b["fuente"] and b["fecha"] >= a["fecha"]:
                out.append({"de": b["sid"], "a": a["sid"], "relacion": rel, "base": ["claude"],
                            "motivo": str(r.get("motivo", ""))[:140], "origen": "claude"})
        cautelas = [str(x)[:160] for x in (d.get("cautelas") or []) if isinstance(x, str)][:3]
        return {"relaciones": out, "cautelas": cautelas}

    # ---------- 3. comité (debate) ----------
    def committee(self, pregunta, contexto, label):
        """Postura A (sí) y B (no) en paralelo; un juez decide. Devuelve {'veredicto': bool, 'motivo', ...}."""
        base = f"Pregunta: {pregunta}\nEvidencia:\n{contexto}\n"

        def stance(lado):
            return self._call(f"comite_{lado}", [pregunta, contexto],
                              base + f"Argumenta la postura '{lado.upper()}' en máximo 60 palabras, citando sids. "
                                     'JSON: {"argumento":"..."}', 300, label)

        with ThreadPoolExecutor(2) as ex:
            si, no = ex.map(stance, ["si", "no"])
        if not si or not no:
            return None
        juez = self._call("comite_juez", [pregunta, contexto, si, no],
                          base + f"Postura SÍ: {si.get('argumento')}\nPostura NO: {no.get('argumento')}\n"
                                 "Como juez imparcial, decide con base SOLO en la evidencia. "
                                 'JSON: {"veredicto":"si|no","motivo":"máx. 25 palabras"}', 300, label)
        if not isinstance(juez, dict) or juez.get("veredicto") not in ("si", "no"):
            return None
        with self.lock:
            self.stats["comites"] += 1
        return {"pregunta": pregunta, "si": si.get("argumento", ""), "no": no.get("argumento", ""),
                "veredicto": juez["veredicto"] == "si", "motivo": juez.get("motivo", "")}

    # ---------- 4. resumen ejecutivo ----------
    def summary(self, sig):
        rows = "\n".join(f"{c['sid']} | {c.get('superada') or c['tipo']} | {c['texto']}" for c in sig["claims"])
        prompt = (f"Señal: {sig['titulo']} (score {sig['score']}/100)\nAfirmaciones (sid | estado | texto):\n{rows}\n"
                  "Restricciones (Lo que NO afirmo):\n" + "\n".join(sig["no_afirmo"]) +
                  "\n\nRedacta un resumen ejecutivo en español de máximo 90 palabras: qué se sabe (hechos), qué se "
                  "sospecha (hipótesis), qué falta y qué cambió por evidencia posterior. Cita cada afirmación con su sid "
                  "entre corchetes, p.ej. [F01.2]. No inventes cifras. "
                  'JSON: {"resumen":"..."}')
        key = [sig["titulo"], [(c["sid"], c.get("superada") or c["tipo"]) for c in sig["claims"]], sig["no_afirmo"]]
        d = self._call("resumen", key, prompt, 600, sig["titulo"])
        txt = (d or {}).get("resumen", "") if isinstance(d, dict) else ""
        if not txt:
            return None
        _, bad, ok = llm._check(txt, [c["sid"] for c in sig["claims"]])
        return txt if ok else None

    def motor(self):
        return {"modo": "claude", "modelo": self.model, **self.stats, "costo_usd": round(self.stats["costo_usd"], 5)}
