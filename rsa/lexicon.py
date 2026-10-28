"""Lexicón de dominio. Único lugar con conocimiento 'experto': editable y auditable.
Todos los patrones se aplican sobre texto normalizado (sin tildes, minúsculas)."""

# Términos con potencial económico (palancas de ingreso/costo)
ECON = {
    "tasa": 2, "prima": 3, "cobro": 3, "cobra": 3, "comision": 3, "tarifa": 3, "tarifario": 3, "ingreso": 3,
    "membresia": 3, "exoneracion": 2, "desgravamen": 2, "devengo": 2, "flujo": 1, "costo": 1, "retencion": 1,
    "canibalizacion": 2, "materialidad": 2, "cuentas contables": 2, "desviacion": 2, "mensual": 1, "anual": 1,
    "fecha de pago": 2, "dia de pago": 2, "calendario de pagos": 2, "parametrizacion": 1, "rate_input": 2,
}

# Declaraciones explícitas de NO impacto económico → ruido
NO_IMPACT = [
    r"no cambia ninguna (tarifa|condicion)", r"no existe vinculo identificado con (precios|cobros)",
    r"no afectara los canales productivos", r"no se modificaran (tarifas|promociones)",
    r"no (cambia|modifica|afecta)[^.]{0,40}(tarifa|cobro|precio|producto)",
]

# Clasificación de afirmaciones (orden = prioridad)
FALTANTE = [
    r"no se (ha|han) confirmado", r"nadie confirma", r"no se encuentra", r"no dispone", r"se desconoce",
    r"no incluye", r"no se adjuntan", r"no proporciona", r"aun no se ha conciliado", r"no se ha conciliado",
    r"debe(n)? (verificarse|confirmar|contrastar)", r"se solicita", r"solicita (contrastar|vincular|no )",
    r"no distingue", r"sin controlar", r"no esta ajustada",
    r"no representa", r"no permite", r"no cubre", r"pendiente", r"\bfalta", r"todavia no", r"aun no",
]
ADVERTENCIA = [r"inducir a error", r"no debe asumirse", r"antes de (concluir|inferir|retirar)", r"no hacerlo hasta",
               r"sin evidencia"]
CORRECCION = [r"corregir", r"aclaracion", r"no existe todavia", r"se utilizo [^.]* para describir una demostracion",
              r"maqueta", r"\baclara\b", r"correspondia al entorno", r"en realidad", r"se rectifica", r"queda sin efecto", r"desmiente"]
HIPOTESIS = [
    r"parece", r"podria(n)?", r"anticipa", r"estaria", r"eventual", r"preliminar", r"aparentemente",
    r"planea", r"en evaluacion", r"propon", r"sugiere", r"interpretaron", r"evaluando", r"recuerda",
    r"advierte",
]

# Términos de estado para detectar contradicciones de polaridad entre fuentes
STATUS = {  # grupos de conceptos equivalentes
    "habilitacion": ["habilit"],
    "produccion": ["produccion", "productiv", "despleg"],
    "activacion": ["activ", "vigent"],
    "aprobacion": ["aprob"],
}
NEG = r"\b(no|sin|ningun[ao]?|todavia no|aun no|nunca)\b"

# Riesgos de sobreafirmación → reglas del panel "Lo que NO afirmo"
GUARDRAILS = [
    (r"(prima|cobro|tasa).*(inferior|menor|desviacion)|desviacion",
     "No cuantifico pérdida/fuga: la comparación no controla saldo, periodo ni elegibilidad."),
    (r"\b(eliminar\w*|retirar|depurar)\b",
     "No recomiendo eliminar/retirar nada sin conciliar tarifa ↔ transacción ↔ cuenta contable y medir materialidad."),
    (r"habilitad|piloto",
     "No asumo que exista piloto productivo: el estado debe confirmarse con evidencia de despliegue."),
    (r"retencion|ampliar|ampliacion|extender",
     "No asumo impacto neto positivo: falta modelar elegibles, canibalización y valor incremental."),
    (r"muestra (es )?pequena|no representa",
     "No extrapolo a toda la cartera: muestra no representativa."),
    (r"produccion|certificacion",
     "No afirmo estado productivo: la evidencia no distingue producción de certificación/demo."),
]

# Palancas (regex): titulan señales y refuerzan el agrupamiento temático
PALANCAS = [
    ("Posible desviación en cobro de seguro", [r"desgravamen", r"\bprimas?\b", r"rate_input"]),
    ("Comisiones y tarifas: cobro y conciliación", [r"comision", r"tarifari", r"\btarifas?\b", r"\bfees?\b"]),
    ("Exoneración de membresía: retención vs. ingreso", [r"exoneracion", r"membresia"]),
    ("Cambio de calendario / día de pago", [r"fechas? de pago", r"dias? de pago", r"calendario de pagos", r"selector de fechas"]),
]
# Qué cubre cada palanca (se entrega a Claude para que agrupe bien y no invente palancas)
PALANCA_DESC = {
    "Posible desviación en cobro de seguro": "primas y tasas de seguros (p.ej. desgravamen), parametrización de la tasa por canal "
        "(rate_input, anual vs. mensual, conversión/mensualización), diferencias de prima entre canales",
    "Comisiones y tarifas: cobro y conciliación": "comisiones, fees, tarifas y cargos: cobro o no cobro, vigencia, depuración del "
        "tarifario, conciliación con transacciones y cuentas contables, materialidad",
    "Exoneración de membresía: retención vs. ingreso": "exoneraciones o waivers de membresía/cuotas, campañas de retención, umbrales "
        "de consumo por segmento, canibalización e impacto en ingresos",
    "Cambio de calendario / día de pago": "fechas o días de pago, calendario de cuotas, selector de fecha, pilotos o maquetas "
        "asociadas, reclamos por fechas, devengo y reglas de corte",
}

# Peso de impacto por palanca (0–1): directo en ingreso > indirecto
IMPACTO = {
    "Posible desviación en cobro de seguro": 0.9,
    "Comisiones y tarifas: cobro y conciliación": 0.7,
    "Exoneración de membresía: retención vs. ingreso": 0.65,
    "Cambio de calendario / día de pago": 0.45,
}

# Catálogo para la política de consulta de la herramienta local
PRODUCTOS = ["credito flexible", "tarjeta tc"]
CANALES = {"web": "Web", "banca web": "Web", "sucursal": "Sucursal", "app": "App"}
CANAL_CONTRASTE = {"Web": "Sucursal"}   # baseline para comparar configuraciones entre canales
PARAMETROS = {
    "rate_input": ["rate_input", "tasa anual de seguro"],
    "selector_dia_pago": ["selector de fechas", "dia de pago", "fechas de pago"],
    "exoneracion_membresia": ["exoneracion de membresia"],
}
