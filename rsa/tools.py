"""Política de consulta a la herramienta local (consultar_parametros.py).
Se invoca solo si la señal permite inferir PRODUCTO + CANAL + PARÁMETRO desde sus fuentes.
Cada decisión (invocar u omitir) queda en el log de trazabilidad."""
from __future__ import annotations

import contextlib
import io
import json
import re
import runpy
import sys
import time
from pathlib import Path

from . import lexicon as L
from .text import norm

TOOL_NAMES = {"credito flexible": "Credito Flexible", "tarjeta tc": "Tarjeta TC"}


def invoke(tool_path: Path, producto, canal, parametro) -> dict:
    """Ejecuta la herramienta SIN modificarla, en proceso (runpy con argv propio): funciona igual en
    Python y dentro de un .exe empaquetado, sin depender de un intérprete externo."""
    t0 = time.perf_counter()
    buf, argv = io.StringIO(), sys.argv
    try:
        sys.argv = [str(tool_path), producto, canal, parametro]
        with contextlib.redirect_stdout(buf):
            runpy.run_path(str(tool_path), run_name="__main__")
    except SystemExit:
        pass
    except Exception as e:  # herramienta caída → se registra, no rompe el análisis
        buf.write(json.dumps({"error": repr(e)}))
    finally:
        sys.argv = argv
    try:
        res = json.loads(buf.getvalue())
    except json.JSONDecodeError:
        res = {"error": buf.getvalue().strip()}
    return {"args": [producto, canal, parametro], "resultado": res, "ms": round((time.perf_counter() - t0) * 1000)}


def plan(sig) -> dict:
    t = norm(" ".join(c["texto"] for c in sig["claims"]))
    prod = next((p for p in L.PRODUCTOS if p in t), None)
    pos = [(m.start(), v) for k, v in L.CANALES.items() for m in [re.search(rf"\b{k}\b", t)] if m]
    canal = min(pos)[1] if pos else None  # canal mencionado primero = canal objeto de la señal
    param = next((k for k, al in L.PARAMETROS.items() if any(a in t for a in al)), None)
    # Respaldo: entidades extraídas por Claude (texto informal o en inglés), solo si existen en el catálogo
    for e in sig.get("entidades_ai") or []:
        p_ai = norm(str(e.get("producto") or ""))
        prod = prod or next((p for p in L.PRODUCTOS if p and p in p_ai), None)
        c_ai = str(e.get("canal") or "")
        canal = canal or (c_ai if c_ai in L.CANALES.values() else None)
        x_ai = str(e.get("parametro") or "")
        param = param or (x_ai if x_ai in L.PARAMETROS else None)
    faltan = [n for n, v in (("producto", prod), ("canal", canal), ("parametro", param)) if not v]
    contraste = L.CANAL_CONTRASTE.get(canal) if re.search(r"otros canales|entre canales", t) else None
    return {"producto": TOOL_NAMES.get(prod, prod), "canal": canal, "parametro": param, "faltan": faltan,
            "contraste": contraste}


def interpret(calls) -> str:
    rows = []
    for c in calls:
        regs = c["resultado"].get("registros", [])
        if not regs:
            rows.append(f"{c['args'][1]}: sin registro")
        for r in regs:
            rows.append(f"{r['canal']}: valor={r['valor_configurado']}, estado={r['estado_produccion']}, "
                        f"esperado={r['unidad_esperada']}, rev={r['ultima_revision']}")
    return " | ".join(rows)


def explain(sig, args, contraste=False):
    """Por qué se hizo esta consulta: motivo y oraciones de la evidencia que definieron producto/canal/parámetro
    (o que pidieron contrastar canales)."""
    prod, canal, param = args
    al = [norm(prod)] + [k for k, v in L.CANALES.items() if v == canal] + [norm(a) for a in L.PARAMETROS.get(param, [param])]
    claims = [c for c in sig["claims"] if not c["texto"].startswith("Fila ")]
    if contraste:
        ev = [c["sid"] for c in claims if re.search(r"contrast\w* .*otros canales|otros canales", norm(c["texto"]))]
        motivo = (f"Contraste: la evidencia pide comparar el valor de {next((k for k, v in L.CANAL_CONTRASTE.items() if v == canal), 'el canal observado')} con otros canales "
                  f"antes de concluir que hay un defecto; se usa {canal} como canal de referencia.")
    else:
        ev = [c["sid"] for c in claims if any(re.search(rf"\b{re.escape(a)}\b", norm(c["texto"])) for a in al)]
        motivo = (f"La evidencia identifica producto ({prod}), canal ({canal}) y parámetro ({param}): se puede "
                  "verificar en el sistema lo que las fuentes solo sospechan.")
    return motivo, ev[:4]


def make_runner(tool_path: Path, max_calls=2):
    def run(sig, by_id, log):
        pl = plan(sig)
        if pl["faltan"]:
            log.append({"accion": "consulta_omitida", "senal": sig["titulo"],
                        "motivo": f"no inferible desde fuentes: {', '.join(pl['faltan'])}", "plan": pl})
            return []
        canales = [pl["canal"]] + ([pl["contraste"]] if pl["contraste"] else [])
        calls = [invoke(tool_path, pl["producto"], c, pl["parametro"]) for c in canales[:max_calls]]
        for c in calls:
            log.append({"accion": "consulta_herramienta", "senal": sig["titulo"], "args": c["args"],
                        "motivo": "contraste entre canales solicitado en fuentes" if c["args"][1] == pl["contraste"]
                        else "producto/canal/parámetro explícitos en fuentes",
                        "resultado": c["resultado"], "ms": c["ms"]})
        for c in calls:
            c["contraste"] = c["args"][1] == pl["contraste"]
            c["motivo"], c["evidencia"] = explain(sig, c["args"], c["contraste"])
            c["lectura"] = interpret([c])
            revs = [r["ultima_revision"] for r in c["resultado"].get("registros", [])]
            post = [f for f in sig["fuentes"] if revs and by_id[f].fecha > max(revs)]
            if post:  # evidencia documental posterior al registro: el registro no prevalece por sí solo
                c["posteriores"] = post
                c["lectura"] += f" · registro anterior a {', '.join(post)}: contrastar"
        return calls
    return run
