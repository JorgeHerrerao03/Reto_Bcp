"""Capa agentic OPCIONAL con Claude (API de Anthropic, vía urllib: sin dependencias).
Tres usos, todos con guardrails: cada cita [Fxx.n] debe existir; sin cifras inventadas; si falla → None
y el sistema sigue en modo determinístico. Datos del reto 100% sintéticos.

Configuración (en orden): variables de entorno → archivo .env junto al proyecto (no se sube a git).
  ANTHROPIC_API_KEY=sk-ant-...      RSA_MODEL=claude-haiku-5-5
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

_ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
ENV_F = _ROOT / ".env"
DEFAULT_MODEL = "claude-haiku-5-5"
# USD por millón de tokens (Haiku 5.5, prompts ≤100k). Editable vía RSA_PRICE_IN / RSA_PRICE_OUT
PRICES = {"claude-haiku-5-5": (0.10, 0.50)}
NUM = re.compile(r"\d[\d.,]*\s*(%|soles|s/\.?|usd|\$|millones|mil\b)", re.I)


# ---------- configuración ----------
def _dotenv():
    out = {}
    if ENV_F.exists():
        for line in ENV_F.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def cfg():
    d = _dotenv()
    get = lambda k, default=None: os.getenv(k) or d.get(k) or default
    model = get("RSA_MODEL", DEFAULT_MODEL)
    pin, pout = PRICES.get(model, (1.0, 5.0))
    return {"key": get("ANTHROPIC_API_KEY"), "model": model,
            "price_in": float(get("RSA_PRICE_IN", pin)), "price_out": float(get("RSA_PRICE_OUT", pout))}


def save_cfg(key=None, model=None):
    d = _dotenv()
    if key is not None:
        d["ANTHROPIC_API_KEY"] = key.strip()
    if model:
        d["RSA_MODEL"] = model.strip()
    ENV_F.write_text("".join(f"{k}={v}\n" for k, v in d.items() if v), encoding="utf-8")


def status():
    c = cfg()
    k = c["key"]
    return {"configurada": bool(k), "key": (k[:10] + "…" + k[-4:]) if k else None, "modelo": c["model"],
            "precio_usd_mtok": [c["price_in"], c["price_out"]]}


# ---------- llamada ----------
def call(prompt, max_tokens=500, system=None):
    c = cfg()
    if not c["key"]:
        raise RuntimeError("Sin ANTHROPIC_API_KEY (configúrala en la app o en .env)")
    body = {"model": c["model"], "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
    if system:
        body["system"] = system
    req = urllib.request.Request(os.getenv("RSA_API_URL", "https://api.anthropic.com/v1/messages"), data=json.dumps(body).encode(),
                                 headers={"x-api-key": c["key"], "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"})
    t0 = time.perf_counter()
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=60).read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"API {e.code}: {e.read().decode(errors='replace')[:300]}") from None
    txt = "".join(b.get("text", "") for b in r.get("content", []))
    u = r.get("usage", {})
    cost = (u.get("input_tokens", 0) * c["price_in"] + u.get("output_tokens", 0) * c["price_out"]) / 1e6
    return txt.strip(), {"modelo": c["model"], "tokens": u, "costo_usd": round(cost, 6),
                         "ms": round((time.perf_counter() - t0) * 1000)}


def test():
    txt, meta = call("Responde solo: OK", max_tokens=5)
    return {"respuesta": txt, **meta}


SYS = ("Eres analista de Revenue Optimization en un banco. Usas SOLO la evidencia entregada, citas cada "
       "afirmación con su ID entre corchetes como [F01.2], distingues hecho / hipótesis / faltante, "
       "no inventas ni estimas cifras y no recomiendas eliminar nada sin evidencia. Respondes en español.")


def _check(txt, valid):
    cited = set(re.findall(r"\[(F\d+\.\d+)\]", txt))
    bad = sorted(cited - set(valid))
    return cited, bad, bool(cited) and not bad and not NUM.search(txt)


def _claims(sig):
    return "\n".join(f"{c['sid']} | {c.get('superada') or c['tipo']} | {c['texto']}" for c in sig["claims"])


# ---------- 1. resumen ejecutivo por señal ----------
def summarize(sig, log):
    prompt = (f"Resumen ejecutivo de máximo 90 palabras de esta señal.\nSeñal: {sig['titulo']}\n"
              f"Afirmaciones (sid | estado | texto):\n{_claims(sig)}\n"
              f"Restricciones (Lo que NO afirmo):\n" + "\n".join(sig["no_afirmo"]))
    try:
        txt, meta = call(prompt, 400, SYS)
    except Exception as e:
        log.append({"accion": "llm_omitido", "senal": sig["titulo"], "motivo": str(e)[:200]})
        return None
    cited, bad, ok = _check(txt, [c["sid"] for c in sig["claims"]])
    log.append({"accion": "llm_resumen", "senal": sig["titulo"], **meta, "citas": sorted(cited),
                "citas_invalidas": bad, "aceptado": ok})
    return txt if ok else None


# ---------- 2. preguntar a las fuentes (RAG con citas validadas) ----------
def answer(question, hits):
    ctx = "\n".join(f"{h['sid']} | {h['fecha']} | {h['texto']}" for h in hits)
    prompt = (f"Pregunta: {question}\n\nEvidencia recuperada (sid | fecha | texto):\n{ctx}\n\n"
              "Responde en máximo 120 palabras. Si la evidencia no alcanza, dilo y nombra qué falta. "
              "Si hay fuentes que se contradicen, prioriza la más reciente y menciónalo.")
    txt, meta = call(prompt, 500, SYS)
    cited, bad, ok = _check(txt, [h["sid"] for h in hits])
    return {"respuesta": txt, "aceptada": ok, "citas_invalidas": bad, **meta}


# ---------- 3. segunda opinión sobre un documento nuevo ----------
def review_new_doc(src, signals, log):
    mine = [s for s in signals if src.id in s["fuentes"]]
    ctx = _claims(mine[0]) if mine else "\n".join(f"{s['id']}: {s['titulo']}" for s in signals)
    new = "\n".join(f"{x['sid']} | {x['texto']}" for x in src.sents)
    prompt = (f"Documento nuevo (sid | texto):\n{new}\n\nEvidencia existente (sid | estado | texto):\n{ctx}\n\n"
              "Devuelve SOLO un JSON: {\"relaciones\":[{\"nuevo\":\"F..\",\"relacion\":\"refuta|confirma|resuelve|"
              "matiza\",\"existente\":\"F..\",\"motivo\":\"...\"}],\"riesgo_sobreafirmacion\":\"...\"}. "
              "Solo relaciones claras; lista vacía si no hay.")
    try:
        txt, meta = call(prompt, 700, SYS)
        data = json.loads(txt[txt.index("{"): txt.rindex("}") + 1])
    except Exception as e:
        log.append({"accion": "llm_revision_omitida", "motivo": str(e)[:200]})
        return None
    valid_new = {x["sid"] for x in src.sents}
    valid_old = {c["sid"] for s in mine for c in s["claims"]}
    rels = [r for r in data.get("relaciones", []) if r.get("nuevo") in valid_new and r.get("existente") in valid_old]
    log.append({"accion": "llm_revision_doc", **meta, "propuestas": len(data.get("relaciones", [])),
                "validas": len(rels)})
    return {"relaciones": rels, "riesgo": data.get("riesgo_sobreafirmacion", ""), **meta}
