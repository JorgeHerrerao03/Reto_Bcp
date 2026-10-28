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
            c["lectura"] = interpret([c])
            revs = [r["ultima_revision"] for r in c["resultado"].get("registros", [])]
            post = [f for f in sig["fuentes"] if revs and by_id[f].fecha > max(revs)]
            if post:  # evidencia documental posterior al registro: el registro no prevalece por sí solo
                c["posteriores"] = post
                c["lectura"] += f" · registro anterior a {', '.join(post)}: contrastar"
        return calls
    return run
