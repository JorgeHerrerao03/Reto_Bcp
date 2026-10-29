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
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import lexicon as L
from . import llm
from .text import tokens

PROMPT_VER = "v3"
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
    """Primer objeto JSON del texto (tolera ```json …``` y texto alrededor)."""
    txt = re.sub(r"^```(?:json)?|```$", "", (txt or "").strip(), flags=re.M).strip()
    i = txt.find("{")
    if i < 0:
        raise ValueError("respuesta sin JSON" + (f": {txt[:80]!r}" if txt else " (vacía)"))
    return json.JSONDecoder().raw_decode(txt[i:])[0]


class Brain:
    def __init__(self, cache_file: Path):
        self.cache_file = Path(cache_file)
        self.lock = threading.Lock()
        try:
            self.cache = json.loads(self.cache_file.read_text(encoding="utf-8"))
        except Exception:
            self.cache = {}
        self.model = llm.cfg()["model"]
        self.stats = {"llamadas": 0, "cache": 0, "costo_usd": 0.0, "fallos": 0, "comites": 0, "etapas": {}}
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
                self.stats["etapas"].setdefault(kind.split("_")[0], {"ok": 0, "fallo": 0})["ok"] += 1
                self.events.append({"accion": f"claude_{kind}", "objeto": label, "cache": True})
                return self.cache[ck]
        data, err, mt = None, "", max_tokens
        for intento in (1, 2):  # un reintento acotado: más espacio si se truncó, mismo prompt si el formato falló
            try:
                txt, meta = llm.call(prompt, mt, SYS, temperature=0)
            except Exception as e:
                err = str(e)
                break
            with self.lock:  # el consumo se registra ANTES de interpretar: una respuesta inválida también cuesta
                self.stats["llamadas"] += 1
                self.stats["costo_usd"] += meta["costo_usd"]
            try:
                data = _parse(txt)
                if meta.get("stop_reason") == "max_tokens" and not isinstance(data, dict):
                    raise ValueError("respuesta truncada")
                break
            except Exception as e:
                err = f"{e} · stop_reason={meta.get('stop_reason')}"
                if meta.get("stop_reason") == "max_tokens":
                    mt = int(mt * 2)
        with self.lock:
            st = self.stats["etapas"].setdefault(kind.split("_")[0], {"ok": 0, "fallo": 0})
        if data is None:
            with self.lock:
                self.stats["fallos"] += 1
                st["fallo"] += 1
                self.events.append({"accion": f"claude_{kind}_fallo", "objeto": label, "error": err[:200]})
            return None
        with self.lock:
            st["ok"] += 1
            self.events.append({"accion": f"claude_{kind}", "objeto": label, "cache": False, "ms": meta["ms"],
                                "tokens": meta["tokens"], "costo_usd": meta["costo_usd"], "intentos": intento,
                                "stop_reason": meta.get("stop_reason")})
            self.cache[ck] = data
        return data

    # ---------- 1. fuente ----------
    def _source_prompt(self, s):
        sents = "\n".join(f"{x['sid']} | {x['texto']}" for x in s.sents)
        return (f"Fuente {s.id} · {s.fecha} · {s.tipo} · {s.area}\nTítulo: {s.titulo}\nOraciones (sid | texto):\n{sents}\n\n"
                "Palancas económicas conocidas (nombre: qué cubre):\n" +
                "\n".join(f"- {k}: {v}" for k, v in L.PALANCA_DESC.items()) +
                "\nREGLA DE PALANCA: elige SIEMPRE una palanca conocida si el tema encaja aunque sea parcialmente "
                "(un aspecto técnico, un canal o un producto específico de esa palanca sigue siendo esa palanca). "
                "Usa 'nueva: <nombre>' SOLO si el tema no encaja en ninguna de las cuatro.\n"
                f"Definiciones de tipo: {DEF_TIPOS}\n"
                "Relevante = tiene vínculo con ingresos, cobros, tarifas, precios, comisiones, costos, condiciones "
                "comerciales o productos financieros. Es ruido si declara no tener ese vínculo o trata solo temas internos "
                "(marca, infraestructura, bienestar, dashboards).\n"
                "Devuelve JSON:\n"
                '{"relevante": true|false, "motivo_ruido": "texto corto o null", "sid_ruido": "sid que lo prueba o null",'
                ' "palanca": "nombre EXACTO de una palanca conocida, o \'nueva: <nombre corto>\' solo si ninguna encaja, o null",'
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
        p = self._map_palanca(p)
        sid_r = d.get("sid_ruido") if d.get("sid_ruido") in valid else None
        return {"relevante": bool(d.get("relevante", True)), "motivo_ruido": d.get("motivo_ruido") or "",
                "sid_ruido": sid_r, "palanca": p, "operacional": bool(d.get("operacional")),
                "producto": d.get("producto"), "canal": d.get("canal"), "parametro": d.get("parametro"),
                "terminos": [str(t) for t in (d.get("terminos") or [])][:8], "oraciones": ora}

    @staticmethod
    def _map_palanca(p):
        """Nombre exacto → conocida; nombre aproximado (≥50 % de palabras) → conocida; 'nueva: X' → X."""
        if not isinstance(p, str) or not p.strip():
            return None
        p = p.strip()
        if p in PALANCAS:
            return p
        if p.lower().startswith("nueva") and ":" in p:
            return p.split(":", 1)[1].strip().capitalize() or None
        w = set(tokens(p))
        best = max(((len(w & set(tokens(k))) / (len(set(tokens(k))) or 1), k) for k in PALANCAS), default=(0, None))
        return best[1] if best[0] >= 0.5 else p.capitalize()

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
        _, bad, ok = llm._check(txt, [c["sid"] for c in sig["claims"]], {c["sid"]: c["texto"] for c in sig["claims"]})
        return txt if ok else None

    # ---------- brief estratégico ----------
    def strategic(self, sig, prompt):
        return self._call("brief", [sig["titulo"], prompt], prompt, 2000, sig["titulo"])

    # ---------- 5. transcripción de imagen / PDF ----------
    def transcribe(self, data: bytes, media_type: str, filename: str):
        import base64
        if len(data) > 4_500_000:
            raise ValueError("Archivo demasiado grande para transcribir (máx. ~4.5 MB)")
        kind = "document" if media_type == "application/pdf" else "image"
        content = [{"type": kind, "source": {"type": "base64", "media_type": media_type,
                                             "data": base64.b64encode(data).decode()}},
                   {"type": "text", "text": (
                       f"Transcribe fielmente el contenido de '{filename}' para usarlo como fuente de evidencia.\n"
                       "Reglas: copia el texto literal (cualquier idioma); NO interpretes, NO resumas, NO agregues datos. "
                       "Tablas: una línea por fila con el formato 'Fila n · columna: valor | columna: valor'. "
                       "Capturas de sistema: primera línea 'Captura de pantalla de <sistema o pantalla>', luego una línea "
                       "por campo visible 'campo: valor'. Marca [ilegible] lo que no se pueda leer.\n"
                       'JSON: {"titulo":"título corto en español","texto":"transcripción con saltos de línea \\n"}')}]
        d = self._call("transcripcion", {"sha": hashlib.sha1(data).hexdigest(), "mt": media_type}, content, 4000, filename)
        self.save()
        if not isinstance(d, dict) or not str(d.get("texto", "")).strip():
            err = next((e.get("error") for e in reversed(self.events) if "fallo" in e.get("accion", "")), "")
            raise ValueError("Claude no pudo transcribir el archivo" + (f": {err}" if err else ""))
        return str(d.get("titulo") or "").strip(), str(d["texto"]).strip()

    def motor(self):
        m = {"modo": "claude", "modelo": self.model, "prompt_ver": PROMPT_VER, **self.stats, "costo_usd": round(self.stats["costo_usd"], 5),
             "etapas": {k: dict(v) for k, v in self.stats["etapas"].items()}}
        if self.stats["fallos"]:
            caidas = ", ".join(f"{k} {v['fallo']}" for k, v in m["etapas"].items() if v["fallo"])
            m["aviso"] = (f"Claude falló en {self.stats['fallos']} llamada(s) ({caidas}); esos pasos usaron reglas o "
                          "plantilla y quedan marcados")
        return m
