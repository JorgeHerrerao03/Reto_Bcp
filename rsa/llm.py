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
PRICES = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.0, 10.0)}
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
_NO_THINK = {"ok": True}  # se desactiva si el modelo rechaza los parámetros de razonamiento


def call(prompt, max_tokens=500, system=None, temperature=None):
    """Devuelve (texto, meta). meta incluye uso, costo y stop_reason aunque el texto luego no se pueda interpretar.
    Haiku 5.5 piensa por defecto y ese razonamiento consume max_tokens (respuestas vacías o JSON truncado):
    para tareas de extracción se desactiva (RSA_THINKING=adaptive lo reactiva) y se fija effort bajo."""
    c = cfg()
    if not c["key"]:
        raise RuntimeError("Sin ANTHROPIC_API_KEY (configúrala en la app o en .env)")
    body = {"model": c["model"], "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
    if system:
        body["system"] = system
    if _NO_THINK["ok"] and os.getenv("RSA_THINKING", "disabled") == "disabled":
        # Sonnet 5.5 apaga el razonamiento previo con "between_tools"; Haiku 5.5 acepta "disabled"
        body["thinking"] = {"type": "between_tools" if "sonnet" in c["model"] else "disabled"}
        body["output_config"] = {"effort": os.getenv("RSA_EFFORT", "low")}
    # Modelos recientes no aceptan `temperature`: la reproducibilidad se logra con caché por contenido
    if temperature is not None and os.getenv("RSA_TEMPERATURE"):
        body["temperature"] = float(os.getenv("RSA_TEMPERATURE"))
    url = os.getenv("RSA_API_URL", "https://api.anthropic.com/v1/messages")
    hdr = {"x-api-key": c["key"], "anthropic-version": "2023-06-01", "content-type": "application/json"}
    t0 = time.perf_counter()
    try:
        r = json.loads(urllib.request.urlopen(urllib.request.Request(url, data=json.dumps(body).encode(), headers=hdr),
                                              timeout=90).read())
    except urllib.error.HTTPError as e:
        msg = e.read().decode(errors="replace")[:300]
        if e.code == 400 and "thinking" in body and re.search(r"thinking|output_config|effort", msg):
            _NO_THINK["ok"] = False  # modelo sin soporte: reintenta sin esos parámetros
            return call(prompt, max_tokens, system, temperature)
        raise RuntimeError(f"API {e.code}: {msg}") from None
    txt = "".join(b.get("text", "") for b in r.get("content", []) if b.get("type", "text") == "text")
    u = r.get("usage", {})
    cost = (u.get("input_tokens", 0) * c["price_in"] + u.get("output_tokens", 0) * c["price_out"]) / 1e6
    return txt.strip(), {"modelo": c["model"], "tokens": u, "costo_usd": round(cost, 6),
                         "stop_reason": r.get("stop_reason"), "ms": round((time.perf_counter() - t0) * 1000)}


def test():
    txt, meta = call("Responde solo: OK", max_tokens=5)
    return {"respuesta": txt, **meta}


SYS = ("Eres analista de Revenue Optimization en un banco. Usas SOLO la evidencia entregada, citas cada "
       "afirmación con su ID entre corchetes como [F01.2], distingues hecho / hipótesis / faltante, "
       "no inventas ni estimas cifras y no recomiendas eliminar nada sin evidencia. Respondes en español.")


_NUMTOK = re.compile(r"(?<![\w.,/-])(\d+(?:[.,]\d+)*)(\s*%)?(?![\w])")
_IGNORE = re.compile(r"\[?\b[FS]\d+(?:\.\d+)?\b\]?|\b\d{4}-\d{2}-\d{2}\b")


def _val(x):
    x = x.strip()
    if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", x):
        x = x.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d+,\d+", x):
        x = x.replace(",", ".")
    else:
        x = x.replace(",", "")
    try:
        return round(float(x), 6)
    except ValueError:
        return None


def numbers(t):
    """Cifras de un texto como (valor, es_porcentaje); ignora IDs de fuente/señal y fechas ISO."""
    t = _IGNORE.sub(" ", t or "")
    return [(_val(m.group(1)), bool(m.group(2))) for m in _NUMTOK.finditer(t) if _val(m.group(1)) is not None]


def nums_ok(txt, evidence, small=12):
    """Toda cifra del texto debe existir con el MISMO valor (y '%' si lo lleva) en la evidencia.
    Se toleran conteos pequeños sin unidad (≤ small), p.ej. '3 fuentes'."""
    ev = numbers(" ".join(evidence))
    ev_all, ev_pct = {v for v, _ in ev}, {v for v, p in ev if p}
    for v, pct in numbers(txt):
        if pct and v not in ev_pct:
            return False
        if not pct and v not in ev_all and not (float(v).is_integer() and v <= small):
            return False
    return True


def _check(txt, valid, texts=None):
    """Citas válidas y sin cifras inventadas: cada cifra debe aparecer con el mismo valor en la evidencia
    (p.ej. un 'Cálculo (código)' de una tabla). Si se pasan textos por sid, la cifra se contrasta contra las
    oraciones citadas en la misma frase."""
    cited = set(re.findall(r"\[(F\d+\.\d+)\]", txt))
    bad = sorted(cited - set(valid))
    if isinstance(texts, dict):
        ok_n = True
        for frase in re.split(r"(?<=[.;])\s+", txt):
            cs = re.findall(r"\[(F\d+\.\d+)\]", frase)
            ev = [texts[c] for c in cs if c in texts] or list(texts.values())
            ok_n = ok_n and nums_ok(frase, ev)
    else:
        ok_n = nums_ok(txt, texts or [])
    return cited, bad, bool(cited) and not bad and ok_n


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
    cited, bad, ok = _check(txt, [c["sid"] for c in sig["claims"]], {c["sid"]: c["texto"] for c in sig["claims"]})
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
    cited, bad, ok = _check(txt, [h["sid"] for h in hits], {h["sid"]: h["texto"] for h in hits})
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
