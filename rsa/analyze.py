"""Análisis determinístico: relevancia, agrupamiento en señales, clasificación de afirmaciones,
contradicciones y scoring. Sin LLM: reproducible y auditable."""
from __future__ import annotations

import re
from collections import Counter

from . import lexicon as L
from .text import TfIdf, norm, tokens

W_IMPACTO, W_EVIDENCIA, W_URGENCIA = 0.45, 0.30, 0.25
OPERACIONAL = r"detecto|registrad|cobrad|configur|cargad|parametriz|tabla de configuracion"


def _any(pats, t):
    return [p for p in pats if re.search(p, t)]


# ---------- afirmaciones ----------
def classify(texto: str) -> dict:
    t = norm(texto)
    for tipo, pats in (("correccion", L.CORRECCION), ("faltante", L.FALTANTE),
                       ("advertencia", L.ADVERTENCIA), ("hipotesis", L.HIPOTESIS)):
        hit = _any(pats, t)
        if hit:
            return {"tipo": tipo, "cues": hit}
    return {"tipo": "hecho", "cues": []}


# ---------- relevancia ----------
def relevance(src) -> dict:
    t = norm(src.titulo + " " + src.body)
    noimp = _any(L.NO_IMPACT, t)
    if noimp:
        frag = next((s["texto"] for s in src.sents if re.search(noimp[0], norm(s["texto"]))), "")
        return {"relevante": False, "motivo": "Declara explícitamente no impacto económico", "evidencia": frag,
                "econ": 0}
    econ = sum(w for k, w in L.ECON.items() if k in t)
    if econ < 3:
        return {"relevante": False, "motivo": f"Sin términos económicos suficientes (score={econ})", "evidencia": "",
                "econ": econ}
    return {"relevante": True, "motivo": "", "evidencia": "", "econ": econ}


def palanca(text: str):
    t = norm(text)
    scores = {name: sum(len(re.findall(p, t)) for p in pats) for name, pats in L.PALANCAS}
    best = max(scores, key=scores.get)
    return best if scores[best] else None


# ---------- agrupamiento ----------
def cluster(sources, tfidf: TfIdf, thr=0.2, boost=0.25):
    ids = [s.id for s in sources]
    pal = {s.id: palanca(s.titulo + " " + s.body) for s in sources}
    parent = {i: i for i in ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    edges = []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            sim = tfidf.cos(a, b) + (boost if pal[a] and pal[a] == pal[b] else 0)
            if sim >= thr:
                edges.append((a, b, round(sim, 3)))
                parent[find(a)] = find(b)
    groups = {}
    for i in ids:
        groups.setdefault(find(i), []).append(i)
    return list(groups.values()), edges, pal


# ---------- contradicciones ----------
def contradictions(claims, src_by_id):
    """Corrección posterior → refuta hipótesis / resuelve faltantes. Hecho posterior → resuelve faltantes.
    Nunca refuta hechos documentados (política/ficha). Heurística léxica: solapamiento de conceptos de estado
    o >=4 términos de contenido."""
    out = []
    for b in claims:
        if b["tipo"] not in ("correccion", "hecho"):
            continue
        tb, sb, nb = set(tokens(b["texto"])), src_by_id[b["fuente"]], norm(b["texto"])
        for a in claims:
            if a["fuente"] == b["fuente"] or src_by_id[a["fuente"]].fecha > sb.fecha or a["tipo"] in ("correccion", "hecho"):
                continue
            if b["tipo"] == "hecho" and a["tipo"] != "faltante":
                continue
            na = norm(a["texto"])
            status = [g for g, st in L.STATUS.items() if any(x in na for x in st) and any(x in nb for x in st)]
            overlap = set(tokens(a["texto"])) & tb
            if (status and b["tipo"] == "correccion") or len(overlap) >= 4:
                rel = "resuelve" if a["tipo"] == "faltante" else "refuta"
                out.append({"de": b["sid"], "a": a["sid"], "relacion": rel, "base": status or sorted(overlap)[:5]})
    return out


# ---------- scoring ----------
def score(sig: dict, src_by_id, tool_results=()):
    n_f = len(sig["fuentes"])
    areas = {src_by_id[f].area for f in sig["fuentes"]}
    c = Counter(cl["tipo"] for cl in sig["claims"] if not cl.get("superada"))
    tot = sum(c.values()) or 1
    impacto = L.IMPACTO.get(sig["palanca"], 0.5)
    evidencia = 0.4 * min(1, n_f / 4) + 0.3 * min(1, len(areas) / 3) + 0.3 * (c["hecho"] / tot)
    texto = norm(" ".join(cl["texto"] for cl in sig["claims"]))
    operacional = 1 if re.search(OPERACIONAL, texto) else 0
    refutado = any(x["relacion"] == "refuta" for x in sig["contradicciones"])
    tool_flag = 0
    for r in tool_results:
        for reg in r.get("resultado", {}).get("registros", []):
            if reg.get("estado_produccion") in ("sin_confirmacion",) or "pendiente" in str(reg.get("valor_configurado")):
                tool_flag = max(tool_flag, 1)
            if reg.get("estado_produccion") == "no_desplegado":
                refutado = True
    urgencia = max(0.0, min(1.0, 0.4 + 0.4 * operacional + 0.2 * tool_flag - 0.2 * refutado))
    n_ref = sum(1 for cl in sig["claims"] if cl.get("superada") == "refutada")
    penal = min(18, 6 * n_ref)
    total = max(0, 100 * (W_IMPACTO * impacto + W_EVIDENCIA * evidencia + W_URGENCIA * urgencia) - penal)
    conf = "alta" if c["hecho"] / tot >= 0.6 else "media" if c["hecho"] / tot >= 0.3 else "baja"
    return {
        "score": round(total, 1),
        "componentes": {"impacto": round(impacto, 2), "evidencia": round(evidencia, 2), "urgencia": round(urgencia, 2),
                        "penalizacion": penal},
        "pesos": {"impacto": W_IMPACTO, "evidencia": W_EVIDENCIA, "urgencia": W_URGENCIA},
        "conteo": dict(c), "confianza": conf, "areas": sorted(areas),
    }


def guardrails(sig):
    t = norm(" ".join(cl["texto"] for cl in sig["claims"]))
    return [msg for pat, msg in L.GUARDRAILS if re.search(pat, t)]


def next_steps(sig):
    pats = r"se solicita|solicita|debe(n)? (confirmar|verificarse|contrastar)|se sugiere|se acordo|requiere aprobacion"
    return [{"sid": c["sid"], "texto": c["texto"]} for c in sig["claims"]
            if re.search(pats, norm(c["texto"])) and not c.get("superada")]


def analyze(sources, tool_runner=None, log=None):
    log = log if log is not None else []
    by_id = {s.id: s for s in sources}
    rel = {s.id: relevance(s) for s in sources}
    descartadas = [{"fuente": k, **v} for k, v in rel.items() if not v["relevante"]]
    log.append({"accion": "clasificar_relevancia", "nucleo_economico": [k for k, v in rel.items() if v["relevante"]],
                "ruido_explicito": [d["fuente"] for d in descartadas if "no impacto" in d["motivo"]],
                "sin_lexico_economico": [d["fuente"] for d in descartadas if "no impacto" not in d["motivo"]]})
    tf = TfIdf({s.id: s.titulo + " " + s.body for s in sources})
    # 2ª pasada: fuentes sin léxico económico propio pero ligadas temáticamente a una fuente núcleo
    core = [s.id for s in sources if rel[s.id]["relevante"]]
    pal_core = {palanca(by_id[i].titulo + " " + by_id[i].body) for i in core} - {None}
    for s in sources:
        r = rel[s.id]
        if r["relevante"] or r["econ"] == 0 and "no impacto" in r["motivo"]:
            continue
        p = palanca(s.titulo + " " + s.body)
        link = max(((tf.cos(s.id, c), c) for c in core), default=(0, None))
        if p in pal_core or link[0] >= 0.2:
            rel[s.id] = {"relevante": True, "motivo": "", "evidencia": "", "econ": r["econ"],
                         "contextual": f"vinculada por palanca '{p}'" if p in pal_core else f"similitud con {link[1]}"}
    descartadas = [{"fuente": k, **v} for k, v in rel.items() if not v["relevante"]]
    log.append({"accion": "vincular_contextuales",
                "fuentes": {k: v["contextual"] for k, v in rel.items() if v.get("contextual")}})
    relevant = [s for s in sources if rel[s.id]["relevante"]]
    groups, edges, pal = cluster(relevant, tf)
    log.append({"accion": "agrupar_fuentes", "grupos": groups})

    signals = []
    for g in groups:
        g = sorted(g, key=lambda i: (by_id[i].fecha, i))
        claims = []
        for fid in g:
            for s in by_id[fid].sents:
                claims.append({"sid": s["sid"], "fuente": fid, "fecha": by_id[fid].fecha, "texto": s["texto"],
                               **classify(s["texto"])})
        contra = contradictions(claims, by_id)
        refutadas = {x["a"]: x["de"] for x in contra if x["relacion"] == "refuta"}
        resueltas = {x["a"]: x["de"] for x in contra if x["relacion"] == "resuelve"}
        for cl in claims:
            if cl["sid"] in refutadas:
                cl["superada"], cl["por"] = "refutada", refutadas[cl["sid"]]
            elif cl["sid"] in resueltas:
                cl["superada"], cl["por"] = "resuelta", resueltas[cl["sid"]]
        p = Counter(pal[i] for i in g if pal[i]).most_common(1)
        p = p[0][0] if p else None
        sig = {"key": "|".join(g), "palanca": p, "titulo": p or "Señal: " + ", ".join(tf.top_terms(g, 3)),
               "fuentes": g, "terminos": tf.top_terms(g, 6), "claims": claims, "contradicciones": contra}
        sig["consultas"] = tool_runner(sig, by_id, log) if tool_runner else []
        sig.update(score(sig, by_id, sig["consultas"]))
        sig["no_afirmo"] = guardrails(sig)
        sig["proximos_pasos"] = next_steps(sig)
        signals.append(sig)
    signals.sort(key=lambda s: -s["score"])
    edges_all = [{"a": a, "b": b, "w": w} for a, b, w in edges]
    return {"signals": signals, "descartadas": descartadas, "edges": edges_all, "relevancia": rel, "log": log}
