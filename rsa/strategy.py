"""Brief estratégico (formato negocio): oportunidad → por qué importa → objetivo y alcance → lo que sabemos →
lo que necesitamos confirmar → plan de acción → criterios de decisión → riesgos. La evidencia técnica va al anexo.

Con Claude: lo redacta él a partir de la evidencia ya clasificada (citas y cifras validadas).
Sin Claude: plantilla por palanca + evidencia seleccionada. Ambos devuelven el mismo esquema."""
from __future__ import annotations

import re

from .brief import recomendacion

# Plantillas por palanca (respaldo sin LLM)
PLANTILLAS = {
    "Posible desviación en cobro de seguro": {
        "titular": "Validar y corregir el cobro de la prima de seguro en el canal Web",
        "oportunidad": "Asegurar que la prima de desgravamen se cobre correctamente en todos los canales, empezando por Web.",
        "importa": "Un error de parametrización de la tasa se replica en cada crédito originado en el canal: es ingreso "
                   "recurrente que podría estar dejándose de cobrar, además de un riesgo de cumplimiento con el contrato del seguro.",
        "objetivo": "Confirmar o descartar la desviación de prima en Web y, si se confirma, dimensionarla y corregirla.",
        "incluye": ["Configuración de la tasa por canal (producción vs. certificación)",
                    "Muestra transaccional comparable (mismo saldo y periodo)", "Corrección y control preventivo"],
        "excluye": ["Recalcular primas históricas sin validación legal", "Cambios a la tarifa aprobada"],
        "decision": [("Se confirma la tasa mal cargada en producción", "Corregir el parámetro, dimensionar el impacto y definir el tratamiento retroactivo con Legal/Seguros"),
                     ("La diferencia se explica por saldo, periodo o elegibilidad", "Cerrar la señal y documentar la conclusión")],
    },
    "Comisiones y tarifas: cobro y conciliación": {
        "titular": "Ordenar el tarifario sin perder ingreso real",
        "oportunidad": "Ordenar el tarifario: conservar lo que genera ingreso y retirar solo lo que, con evidencia, ya no aplica.",
        "importa": "Las comisiones de baja frecuencia pueden seguir siendo materiales; retirarlas sin conciliar puede "
                   "eliminar ingreso real, y no cobrarlas cuando aplican también lo es.",
        "objetivo": "Conciliar cada comisión con transacciones y cuentas contables y decidir, caso por caso, mantener, corregir o retirar.",
        "incluye": ["Inventario de códigos de tarifa", "Conciliación con transacciones y contabilidad", "Medición de materialidad"],
        "excluye": ["Retirar comisiones antes de conciliar", "Rediseño completo del tarifario"],
        "decision": [("La comisión tiene uso y materialidad", "Mantener o corregir el cobro"),
                     ("Sin uso ni materialidad comprobada", "Proponer su retiro con respaldo de Finanzas")],
    },
    "Exoneración de membresía: retención vs. ingreso": {
        "titular": "Ampliar la exoneración solo con un caso de negocio positivo",
        "oportunidad": "Decidir la ampliación de la exoneración de membresía con un caso de negocio que balancee retención e ingreso.",
        "importa": "Exonerar a más clientes puede mejorar la retención, pero reduce el ingreso por membresía; sin el "
                   "modelo de canibalización no se sabe si el efecto neto es positivo.",
        "objetivo": "Construir el caso de negocio (elegibles, canibalización, valor incremental) antes de solicitar la aprobación.",
        "incluye": ["Universo de elegibles por segmento", "Modelo de canibalización e impacto neto", "Piloto controlado"],
        "excluye": ["Ampliar la campaña antes de la aprobación formal"],
        "decision": [("El valor incremental de la retención supera el ingreso cedido", "Aprobar la ampliación por segmento, con control de resultados"),
                     ("El impacto neto es negativo o incierto", "Mantener la política vigente o pilotear en un segmento acotado")],
    },
    "Cambio de calendario / día de pago": {
        "titular": "Día de pago flexible: validar demanda e impacto antes de pilotear",
        "oportunidad": "Evaluar si permitir elegir el día de pago mejora la experiencia del cliente sin deteriorar el devengo ni la mora.",
        "importa": "Puede reducir reclamos y mejorar la puntualidad de pago, pero altera los flujos, el devengo y las reglas de corte.",
        "objetivo": "Validar la preferencia del cliente y simular el impacto financiero antes de pasar de la maqueta a un piloto.",
        "incluye": ["Segmentación de reclamos y preferencias", "Simulación financiera (devengo, flujos, mora)", "Diseño de un piloto"],
        "excluye": ["Despliegue productivo sin simulación ni aprobación"],
        "decision": [("La simulación muestra impacto neutro o positivo y hay demanda", "Aprobar un piloto acotado con métricas de mora y satisfacción"),
                     ("El impacto financiero es negativo o la demanda baja", "Mantener el calendario actual")],
    },
}
GENERICA = {
    "titular": "",
    "oportunidad": "Validar una señal con potencial económico detectada en las fuentes.",
    "importa": "Puede afectar ingresos, costos o la experiencia del cliente; requiere validación antes de actuar.",
    "objetivo": "Confirmar los hechos, cerrar los vacíos de información y decidir si se escala.",
    "incluye": ["Validación de la evidencia", "Dimensionamiento"], "excluye": ["Acciones sin validación"],
    "decision": [("La evidencia se confirma", "Escalar con un plan de acción"), ("No se confirma", "Cerrar la señal")],
}


def _is_row(c):
    return c["texto"].startswith("Fila ") and " · " in c["texto"][:12]


def _pick(sig, tipo, n):
    xs = [c for c in sig["claims"] if c["tipo"] == tipo and not c.get("superada") and not _is_row(c)]
    calc = [c for c in xs if c["texto"].startswith("Cálculo")]
    rest = [c for c in xs if not c["texto"].startswith("Cálculo")]
    return (calc[:2] + list(reversed(rest)))[:n]  # cálculos primero, luego lo más reciente


def _short(t, n=190):
    t = re.sub(r"\s+", " ", t).strip()
    return t if len(t) <= n else t[: n - 1].rsplit(" ", 1)[0] + "…"


def fallback(sig, fuentes) -> dict:
    T = PLANTILLAS.get(sig.get("palanca"), GENERICA)
    area = lambda sid: fuentes.get(sid.split(".")[0], {}).get("area", "Por definir")
    plan = [{"paso": _short(p["texto"], 160), "responsable": area(p["sid"]), "cita": p["sid"]}
            for p in sig["proximos_pasos"][:5]]
    if not plan:
        plan = [{"paso": _short(c["texto"], 160), "responsable": area(c["sid"]), "cita": c["sid"]}
                for c in _pick(sig, "faltante", 3)]
    return {
        "origen": "plantilla",
        "titular": T.get("titular") or sig["titulo"],
        "oportunidad": T["oportunidad"],
        "por_que_importa": T["importa"],
        "objetivo": T["objetivo"],
        "alcance": {"incluye": T["incluye"], "excluye": T["excluye"]},
        "sabemos": [{"texto": _short(c["texto"]), "cita": c["sid"]} for c in _pick(sig, "hecho", 4)],
        "creemos": [{"texto": _short(c["texto"]), "cita": c["sid"]} for c in _pick(sig, "hipotesis", 3)],
        "confirmar": [{"texto": _short(c["texto"]), "cita": c["sid"]} for c in _pick(sig, "faltante", 4)],
        "plan": plan,
        "decision": [{"si": a, "entonces": b} for a, b in T["decision"]],
        "riesgos": sig["no_afirmo"][:4],
    }


SCHEMA = ('{"titular":"frase de negocio, máx. 12 palabras","oportunidad":"1-2 oraciones",'
          '"por_que_importa":"1-2 oraciones sobre impacto en ingreso, riesgo o cliente (sin cifras inventadas)",'
          '"objetivo":"1 oración, verbo en infinitivo","alcance":{"incluye":["..."],"excluye":["..."]},'
          '"sabemos":[{"texto":"hecho clave en lenguaje de negocio","cita":"Fxx.n"}],'
          '"creemos":[{"texto":"hipótesis principal","cita":"Fxx.n"}],'
          '"confirmar":[{"texto":"pregunta concreta a resolver","cita":"Fxx.n"}],'
          '"plan":[{"paso":"acción concreta","responsable":"área","cita":"Fxx.n"}],'
          '"decision":[{"si":"condición observable","entonces":"decisión"}],"riesgos":["..."]}')


def prompt(sig, fuentes):
    rows = "\n".join(f"{c['sid']} | {fuentes.get(c['fuente'], {}).get('area', '')} | {c.get('superada') or c['tipo']} | "
                     f"{c['texto']}" for c in sig["claims"] if not _is_row(c))
    return (f"Redacta un BRIEF ESTRATÉGICO (documento de negocio para un comité, no técnico) para iniciar el trabajo sobre "
            f"esta oportunidad.\nSeñal: {sig['titulo']} · prioridad {sig['score']}/100 · {recomendacion(sig)}\n"
            f"Evidencia (sid | área | estado | texto):\n{rows}\n"
            "Restricciones (lo que NO se puede afirmar):\n" + "\n".join(sig["no_afirmo"]) +
            "\n\nReglas: lenguaje claro y ejecutivo, en español; máximo 4 ítems por lista; cada ítem de sabemos, creemos, "
            "confirmar y plan cita UN sid existente; responsables = áreas que aparecen en la evidencia; las cifras solo se "
            "usan si aparecen literalmente en la evidencia; no recomiendes acciones irreversibles sin validación.\n"
            f"JSON: {SCHEMA}")


def normalize(d, sig, fuentes):
    """Valida la salida de Claude; lo que no cumple se completa con la plantilla."""
    from . import llm
    if not isinstance(d, dict) or not (d.get("oportunidad") and d.get("objetivo")):
        return None
    base = fallback(sig, fuentes)
    valid = {c["sid"] for c in sig["claims"]}
    texts = [c["texto"] for c in sig["claims"]]

    def items(key, fields):
        out = []
        for x in d.get(key) or []:
            if isinstance(x, dict) and x.get("cita") in valid and all(isinstance(x.get(f), str) and x[f].strip() for f in fields):
                out.append({f: x[f].strip()[:240] for f in fields + ["cita"]})
        return out[:4] or base[key]

    b = {"origen": "claude",
         "titular": str(d.get("titular") or base["titular"])[:120],
         "oportunidad": str(d.get("oportunidad") or base["oportunidad"])[:400],
         "por_que_importa": str(d.get("por_que_importa") or base["por_que_importa"])[:400],
         "objetivo": str(d.get("objetivo") or base["objetivo"])[:300],
         "alcance": {k: [str(x)[:160] for x in ((d.get("alcance") or {}).get(k) or [])][:4] or base["alcance"][k]
                     for k in ("incluye", "excluye")},
         "sabemos": items("sabemos", ["texto"]), "creemos": items("creemos", ["texto"]),
         "confirmar": items("confirmar", ["texto"]), "plan": items("plan", ["paso", "responsable"]),
         "decision": [{"si": str(x.get("si"))[:200], "entonces": str(x.get("entonces"))[:200]}
                      for x in (d.get("decision") or []) if isinstance(x, dict) and x.get("si") and x.get("entonces")][:3]
                     or base["decision"],
         "riesgos": [str(x)[:220] for x in (d.get("riesgos") or []) if isinstance(x, str)][:4] or base["riesgos"]}
    blob = " ".join([b["titular"], b["oportunidad"], b["por_que_importa"], b["objetivo"]] +
                    [x["texto"] for k in ("sabemos", "creemos", "confirmar") for x in b[k]] + [x["paso"] for x in b["plan"]])
    ev = " ".join(texts)
    for m in llm.NUM.finditer(blob):  # toda cifra con unidad debe existir literalmente en la evidencia
        if re.match(r"\d[\d.,]*", m.group(0)).group(0).rstrip(".,") not in ev:
            return {**base, "origen": "plantilla (Claude usó cifras no presentes en la evidencia)"}
    return b


def build(sig, fuentes, ai=None):
    if ai:
        try:
            d = ai.strategic(sig, prompt(sig, fuentes))
            b = normalize(d, sig, fuentes)
            if b:
                return b
        except Exception:
            pass
    return fallback(sig, fuentes)
