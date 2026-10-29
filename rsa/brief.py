"""Opportunity Brief (markdown) + traza de investigación por señal."""
from __future__ import annotations

ETQ = {"hecho": "Hecho", "hipotesis": "Hipótesis", "faltante": "Faltante", "advertencia": "Advertencia",
       "correccion": "Corrección"}


def recomendacion(sig):
    if any(c.get("superada") == "refutada" for c in sig["claims"]) and sig["score"] < 55:
        return "Monitorear: evidencia clave refutada; mantener como propuesta"
    if sig["score"] >= 70:
        return "Investigar con prioridad alta (validación antes de cualquier acción)"
    if sig["score"] >= 50:
        return "Investigar (validar supuestos y materialidad)"
    return "Monitorear"


def _q(c):
    return f"> «{c['texto']}» — **[{c['sid']}]**"


def _tesis(sig):
    act = [c for c in sig["claims"] if not c.get("superada")]
    h = next((c for c in act if c["tipo"] == "hipotesis"), None) or next((c for c in act if c["tipo"] == "hecho"), None)
    return h


def strategic_md(sig) -> str:
    B = sig.get("brief")
    if not B:
        return ""
    L = [f"# {B['titular']}", "",
         f"**Opportunity Brief · {sig['id']}** · {sig['titulo']} · Prioridad **{sig['score']}/100** · "
         f"Madurez {sig['confianza']} · Áreas: {', '.join(sig['areas'])}  ",
         f"**Recomendación:** {recomendacion(sig)}", "",
         "## La oportunidad", B["oportunidad"], "",
         "## Por qué importa", B["por_que_importa"], "",
         "## Objetivo", B["objetivo"], "",
         "## Alcance", "**Incluye:** " + "; ".join(B["alcance"]["incluye"]) + "  ",
         "**No incluye:** " + "; ".join(B["alcance"]["excluye"]), ""]
    for k, t in (("sabemos", "Lo que sabemos"), ("creemos", "Lo que creemos (por validar)"),
                 ("confirmar", "Lo que necesitamos confirmar")):
        if B.get(k):
            L += [f"## {t}"] + [f"- {x['texto']} [{x['cita']}]" for x in B[k]] + [""]
    if B.get("plan"):
        L += ["## Plan de acción", "| # | Acción | Responsable | Evidencia |", "|---|---|---|---|"] + [
            f"| {i} | {x['paso']} | {x['responsable']} | {x['cita']} |" for i, x in enumerate(B["plan"], 1)] + [""]
    if B.get("decision"):
        L += ["## Criterios de decisión", "| Si… | Entonces… |", "|---|---|"] + [
            f"| {x['si']} | {x['entonces']} |" for x in B["decision"]] + [""]
    if B.get("riesgos"):
        L += ["## Riesgos y lo que no afirmamos"] + [f"- {r}" for r in B["riesgos"]] + [""]
    return "\n".join(L) + "\n---\n\n"


def render(sig, sources) -> str:
    return strategic_md(sig) + _evidence(sig, sources)


def _evidence(sig, sources) -> str:
    act = [c for c in sig["claims"] if not c.get("superada")]
    by = lambda t: [c for c in act if c["tipo"] == t]
    L = [f"# {'Anexo · Evidencia y trazabilidad' if sig.get('brief') else 'Opportunity Brief'} · {sig['id']} · {sig['titulo']}", "",
         f"**Score:** {sig['score']} / 100 · impacto {sig['componentes']['impacto']} · evidencia "
         f"{sig['componentes']['evidencia']} · urgencia {sig['componentes']['urgencia']}  ",
         f"**Madurez de evidencia:** {sig['confianza']} · **Áreas:** {', '.join(sig['areas'])}  ",
         f"**Recomendación:** {recomendacion(sig)}", ""]
    t = _tesis(sig)
    if t:
        L += ["## Tesis de trabajo (no confirmada)", _q(t), ""]
    for tipo, titulo in (("hecho", "Hechos confirmados en fuentes"), ("hipotesis", "Hipótesis"),
                         ("faltante", "Datos faltantes / pendientes"), ("advertencia", "Advertencias metodológicas"),
                         ("correccion", "Correcciones")):
        xs = by(tipo)
        rows = [c for c in xs if c["texto"].startswith("Fila ")]
        xs = [c for c in xs if not c["texto"].startswith("Fila ")] + rows[:3]
        if xs:
            L += [f"## {titulo}"] + [_q(c) for c in xs]
            if len(rows) > 3:
                L.append(f"> … y {len(rows) - 3} filas más de la tabla (ver fuente {rows[0]['fuente']})")
            L.append("")
    sup = [c for c in sig["claims"] if c.get("superada")]
    if sig["contradicciones"] or sup:
        L += ["## Contradicciones y actualizaciones"]
        for x in sig["contradicciones"]:
            L.append(f"- **[{x['de']}] {x['relacion']} [{x['a']}]** (base: {', '.join(x['base'])})")
        for c in sup:
            L.append(f"- ~~«{c['texto']}» [{c['sid']}]~~ → {c['superada']} por [{c['por']}]")
        L.append("")
    if sig["consultas"]:
        L += ["## Consulta a herramienta local"]
        for c in sig["consultas"]:
            L.append(f"- `consultar_parametros.py {' '.join(repr(a) for a in c['args'])}` → {c['lectura']}")
        adv = sig["consultas"][0]["resultado"].get("advertencia")
        if adv:
            L.append(f"- ⚠ Herramienta: _{adv}_")
        L.append("")
    if sig["no_afirmo"]:
        L += ["## Lo que NO afirmo"] + [f"- {m}" for m in sig["no_afirmo"]] + [""]
    if sig["proximos_pasos"]:
        L += ["## Próximos pasos (derivados de fuentes)"] + [f"- {p['texto']} [{p['sid']}]" for p in
                                                            sig["proximos_pasos"]] + [""]
    L += ["## Fuentes"] + [f"- **{f}** · {sources[f].fecha} · {sources[f].tipo} · {sources[f].area} · "
                           f"{sources[f].titulo}" for f in sig["fuentes"]]
    return "\n".join(L) + "\n"


def trace(sig, log) -> str:
    L = [f"# Traza de investigación · {sig['id']} · {sig['titulo']}", "", "| # | Acción | Detalle |", "|---|---|---|"]
    i = 0
    for e in log:
        if e.get("senal") not in (None, sig["titulo"]):
            continue
        i += 1
        if e["accion"] == "consulta_herramienta":
            det = f"args={e['args']} · motivo: {e['motivo']} · encontrado={e['resultado'].get('encontrado')} · " \
                  f"{e['resultado'].get('registros')} · {e['ms']} ms"
        elif e["accion"] == "consulta_omitida":
            det = e["motivo"]
        elif e["accion"] == "agrupar_fuentes":
            det = f"grupo de la señal: {sig['fuentes']}"
        else:
            det = {k: v for k, v in e.items() if k != "accion"}
        L.append(f"| {i} | {e['accion']} | {str(det).replace('|', '/')} |")
    L += ["", f"**Fuentes consultadas:** {', '.join(sig['fuentes'])}",
          "**Aspectos no resueltos:**"] + [f"- {c['texto']} [{c['sid']}]" for c in sig["claims"]
                                          if c["tipo"] == "faltante" and not c.get("superada")]
    return "\n".join(L) + "\n"
