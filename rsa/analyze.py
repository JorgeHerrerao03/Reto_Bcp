"""Análisis: relevancia, agrupamiento, clasificación de afirmaciones, contradicciones y scoring.
Con Brain (Claude-first) Claude decide y las reglas auditan; sin Brain, todo es determinístico.
El score es siempre determinístico sobre el resultado final."""
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
def cluster(sources, tfidf: TfIdf, thr=0.2, boost=0.25, ai_pal=None):
    ids = [s.id for s in sources]
    ai_pal = ai_pal or {}
    pal = {s.id: ai_pal.get(s.id) or palanca(s.titulo + " " + s.body) for s in sources}
    parent = {i: i for i in ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    edges = []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if ai_pal.get(a) and ai_pal.get(b) and ai_pal[a] != ai_pal[b]:
                continue  # Claude asignó palancas distintas: no se unen
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
    n_conf = sum(1 for x in sig["contradicciones"] if x["relacion"] == "confirma")
    evidencia = min(1.0, 0.4 * min(1, n_f / 4) + 0.3 * min(1, len(areas) / 3) + 0.3 * (c["hecho"] / tot)
                    + min(0.1, 0.03 * n_conf))
    texto = norm(" ".join(cl["texto"] for cl in sig["claims"]))
    operacional = 1 if re.search(OPERACIONAL, texto) or sig.get("operacional_ai") else 0
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
            if (c.get("accion") or re.search(pats, norm(c["texto"]))) and not c.get("superada")]


def _rules_claims(g, by_id):
    return [{"sid": s["sid"], "fuente": fid, "fecha": by_id[fid].fecha, "texto": s["texto"], **classify(s["texto"])}
            for fid in g for s in by_id[fid].sents]


def _apply_relations(claims, contra):
    refutadas = {x["a"]: x["de"] for x in contra if x["relacion"] == "refuta"}
    resueltas = {x["a"]: x["de"] for x in contra if x["relacion"] == "resuelve"}
    confirmadas = {x["a"]: x["de"] for x in contra if x["relacion"] == "confirma"}
    for cl in claims:
        for k in ("superada", "por", "confirmada_por"):
            cl.pop(k, None)
        if cl["sid"] in refutadas:
            cl["superada"], cl["por"] = "refutada", refutadas[cl["sid"]]
        elif cl["sid"] in resueltas:
            cl["superada"], cl["por"] = "resuelta", resueltas[cl["sid"]]
        if cl["sid"] in confirmadas:
            cl["confirmada_por"] = confirmadas[cl["sid"]]


def analyze(sources, tool_runner=None, log=None, ai=None, max_comites=3):
    """ai: Brain (Claude-first) o None (solo reglas). Con ai, Claude decide y las reglas auditan."""
    log = log if log is not None else []
    by_id = {s.id: s for s in sources}
    A = ai.prefetch(sources) if ai else {}
    A = {k: v for k, v in A.items() if v}
    comites = []

    def can_debate():
        return ai and len(comites) < max_comites

    # ---- relevancia: reglas (auditor) y Claude (decisor) ----
    rel = {s.id: relevance(s) for s in sources}
    tf0 = TfIdf({s.id: s.titulo + " " + s.body for s in sources})
    core = [s.id for s in sources if rel[s.id]["relevante"]]
    pal_core = {palanca(by_id[i].titulo + " " + by_id[i].body) for i in core} - {None}
    for s in sources:
        r = rel[s.id]
        if r["relevante"] or "no impacto" in r["motivo"]:
            continue
        p = palanca(s.titulo + " " + s.body)
        link = max(((tf0.cos(s.id, c), c) for c in core), default=(0, None))
        if p in pal_core or link[0] >= 0.2:
            rel[s.id] = {"relevante": True, "motivo": "", "evidencia": "", "econ": r["econ"],
                         "contextual": f"vinculada por palanca '{p}'" if p in pal_core else f"similitud con {link[1]}"}
    rules_rel = {k: v["relevante"] for k, v in rel.items()}
    aud_rel = []
    for s in sources:
        a = A.get(s.id)
        if not a:
            rel[s.id]["decide"] = "reglas"
            continue
        final = a["relevante"]
        if final != rules_rel[s.id]:
            item = {"fuente": s.id, "claude": final, "reglas": rules_rel[s.id], "comite": None}
            if can_debate():
                ctx = "\n".join(f"{x['sid']} | {x['texto']}" for x in s.sents)
                v = ai.committee(f"¿La fuente {s.id} ('{s.titulo}') tiene relevancia económica para el banco "
                                 "(ingresos, cobros, tarifas, comisiones, costos o condiciones de productos)?", ctx, s.id)
                if v:
                    comites.append({"tipo": "relevancia", "objeto": s.id, **v})
                    item["comite"] = v["veredicto"]
                    final = v["veredicto"]
            aud_rel.append(item)
        if final:
            rel[s.id] = {**rel[s.id], "relevante": True, "motivo": "", "evidencia": "", "decide": "claude"}
        else:
            ev = next((x["texto"] for x in s.sents if x["sid"] == a["sid_ruido"]), "") or rel[s.id].get("evidencia", "")
            rel[s.id] = {**rel[s.id], "relevante": False, "decide": "claude",
                         "motivo": a["motivo_ruido"] or rel[s.id].get("motivo") or "Sin vínculo económico (Claude)",
                         "evidencia": ev}
    descartadas = [{"fuente": k, **v} for k, v in rel.items() if not v["relevante"]]
    log.append({"accion": "clasificar_relevancia", "motor": "claude" if A else "reglas",
                "relevantes": [k for k, v in rel.items() if v["relevante"]],
                "descartadas": [d["fuente"] for d in descartadas],
                "discrepancias_reglas": [d["fuente"] for d in aud_rel]})

    # ---- agrupamiento: palanca de Claude + TF-IDF enriquecido con términos traducidos ----
    relevant = [s for s in sources if rel[s.id]["relevante"]]
    tf = TfIdf({s.id: s.titulo + " " + s.body + " " + " ".join((A.get(s.id) or {}).get("terminos", []))
                for s in sources})
    groups, edges, pal = cluster(relevant, tf, ai_pal={k: v["palanca"] for k, v in A.items()})
    log.append({"accion": "agrupar_fuentes", "grupos": groups})

    signals = []
    for g in groups:
        g = sorted(g, key=lambda i: (by_id[i].fecha, i))
        claims = _rules_claims(g, by_id)
        disc = []
        for cl in claims:
            cl["tipo_reglas"] = cl["tipo"]
            a = (A.get(cl["fuente"]) or {}).get("oraciones", {}).get(cl["sid"])
            if a:
                cl.update(tipo=a["tipo"], razon=a["razon"], accion=a["accion"], decide="claude")
                if a["tipo"] != cl["tipo_reglas"]:
                    disc.append({"sid": cl["sid"], "claude": a["tipo"], "reglas": cl["tipo_reglas"], "razon": a["razon"]})
            else:
                cl["decide"] = "reglas"
        p = Counter(pal[i] for i in g if pal[i]).most_common(1)
        p = p[0][0] if p else None
        titulo = p or "Señal: " + ", ".join(tf.top_terms(g, 3))

        rules_rel = contradictions(claims, by_id)
        cl_rel = ai.relations(titulo, claims) if ai and A else None
        cautelas, rel_disp = [], []
        if cl_rel is not None:
            contra, cautelas = list(cl_rel["relaciones"]), cl_rel["cautelas"]
            ks = {(x["de"], x["a"]) for x in contra if x["relacion"] in ("refuta", "resuelve")}
            kr = {(x["de"], x["a"]): x for x in rules_rel}
            disputes = [("claude", x) for x in contra if x["relacion"] in ("refuta", "resuelve") and (x["de"], x["a"]) not in kr]
            disputes += [("reglas", x) for k, x in kr.items() if k not in ks]
            disputes.sort(key=lambda d: by_id[d[1]["de"].split(".")[0]].fecha, reverse=True)
            txt = {c["sid"]: c["texto"] for c in claims}
            for origen, x in disputes:
                item = {"de": x["de"], "a": x["a"], "relacion": x["relacion"], "propone": origen, "comite": None}
                keep = origen == "claude"
                if can_debate():
                    v = ai.committee(f"¿La afirmación {x['de']} {x['relacion']} a la afirmación {x['a']}?",
                                     f"{x['a']} (anterior) | {txt[x['a']]}\n{x['de']} (posterior) | {txt[x['de']]}",
                                     f"{x['de']}→{x['a']}")
                    if v:
                        comites.append({"tipo": "relacion", "objeto": f"{x['de']} {x['relacion']} {x['a']}", **v})
                        item["comite"] = v["veredicto"]
                        keep = v["veredicto"]
                if origen == "claude" and not keep:
                    contra = [c for c in contra if not (c["de"] == x["de"] and c["a"] == x["a"])]
                if origen == "reglas" and keep:
                    contra.append({**x, "origen": "comite"})
                rel_disp.append(item)
        else:
            contra = [{**x, "origen": "reglas"} for x in rules_rel]
        _apply_relations(claims, contra)
        sig = {"key": "|".join(g), "palanca": p, "titulo": titulo, "fuentes": g, "terminos": tf.top_terms(g, 6),
               "claims": claims, "contradicciones": contra,
               "operacional_ai": any((A.get(f) or {}).get("operacional") for f in g),
               "entidades_ai": [{k: (A.get(f) or {}).get(k) for k in ("producto", "canal", "parametro")} for f in g if A.get(f)]}
        sig["consultas"] = tool_runner(sig, by_id, log) if tool_runner else []
        sig.update(score(sig, by_id, sig["consultas"]))
        sig["no_afirmo"] = list(dict.fromkeys(guardrails(sig) + cautelas))
        sig["proximos_pasos"] = next_steps(sig)
        n_ai = sum(1 for c in claims if c["decide"] == "claude")
        sig["auditoria"] = {"motor": "claude" if n_ai else "reglas", "oraciones": len(claims), "por_claude": n_ai,
                            "coinciden": n_ai - len(disc), "discrepancias": disc, "relaciones_en_disputa": rel_disp}
        signals.append(sig)
    signals.sort(key=lambda s: -s["score"])
    if ai:
        ai.save()
        log.extend(ai.events)
        ai.events = []
    edges_all = [{"a": a, "b": b, "w": w} for a, b, w in edges]
    return {"signals": signals, "descartadas": descartadas, "edges": edges_all, "relevancia": rel, "log": log,
            "comites": comites, "auditoria_relevancia": aud_rel, "motor": ai.motor() if ai and A else {"modo": "reglas"}}
