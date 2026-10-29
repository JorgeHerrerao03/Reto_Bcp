# Validar y corregir el cobro de la prima de seguro en el canal Web

**Opportunity Brief · S1** · Posible desviación en cobro de seguro · Prioridad **88.8/100** · Madurez baja · Áreas: Canales Digitales, Operaciones, Seguros, Tecnología  
**Recomendación:** Investigar con prioridad alta (validación antes de cualquier acción)

## La oportunidad
Asegurar que la prima de desgravamen se cobre correctamente en todos los canales, empezando por Web.

## Por qué importa
Un error de parametrización de la tasa se replica en cada crédito originado en el canal: es ingreso recurrente que podría estar dejándose de cobrar, además de un riesgo de cumplimiento con el contrato del seguro.

## Objetivo
Confirmar o descartar la desviación de prima en Web y, si se confirma, dimensionarla y corregirla.

## Alcance
**Incluye:** Configuración de la tasa por canal (producción vs. certificación); Muestra transaccional comparable (mismo saldo y periodo); Corrección y control preventivo  
**No incluye:** Recalcular primas históricas sin validación legal; Cambios a la tarifa aprobada

## Lo que sabemos
- Tecnología reporta: En la sesión de certificación se indicó que la tabla de configuración por canal admite un campo rate_input y que el motor aplica una conversión anual-a-mensual. [F03.1]
- Seguros reporta: La parametrización por canal debe recibir el dato anual; la mensualización la ejecuta el motor de cobros. [F02.2]
- Seguros reporta: Para el producto Crédito Flexible, la tasa de referencia aprobada se expresa anualmente. [F02.1]
- Canales Digitales reporta: En el canal Web de créditos, el sistema espera una tasa anual de seguro y calcula internamente su equivalente mensual. [F01.1]

## Lo que creemos (por validar)
- La alerta se considera preliminar. [F04.6]
- Operaciones detectó que la prima promedio registrada para algunos créditos originados en Web es inferior a la de operaciones aparentemente similares. [F04.1]
- En una revisión de configuración, Andrea comenta que la tasa registrada parece coincidir con el valor mensual informado en la ficha comercial. [F01.2]

## Lo que necesitamos confirmar
- El equipo de operaciones no dispone todavía de una muestra de operaciones con idéntico saldo y periodo de cobertura. [F04.5]
- El archivo adjunto citado en el correo no se encuentra en esta carpeta. [F04.4]
- Se solicita análisis transaccional para confirmar una eventual desviación. [F04.3]
- La comparación no está ajustada por saldos, fechas ni elegibilidad. [F04.2]

## Plan de acción
| # | Acción | Responsable propuesto | Evidencia |
|---|---|---|---|
| 1 | La tasa y la vigencia exactas deben verificarse en la tabla de parámetros autorizada. | Seguros | F02.3 |
| 2 | El equipo solicita contrastar el valor cargado para Web con el de otros canales antes de concluir que hay un defecto. | Tecnología | F03.2 |
| 3 | Se solicita análisis transaccional para confirmar una eventual desviación. | Operaciones | F04.3 |

## Criterios de decisión
| Si… | Entonces… |
|---|---|
| Se confirma la tasa mal cargada en producción | Corregir el parámetro, dimensionar el impacto y definir el tratamiento retroactivo con Legal/Seguros |
| La diferencia se explica por saldo, periodo o elegibilidad | Cerrar la señal y documentar la conclusión |

## Riesgos y lo que no afirmamos
- No cuantifico pérdida/fuga: la comparación no controla saldo, periodo ni elegibilidad.
- No afirmo estado productivo: la evidencia no distingue producción de certificación/demo.

---

# Anexo · Evidencia y trazabilidad · S1 · Posible desviación en cobro de seguro

**Score:** 88.8 / 100 · impacto 0.9 · evidencia 0.77 · urgencia 1.0  
**Madurez de evidencia:** baja · **Áreas:** Canales Digitales, Operaciones, Seguros, Tecnología  
**Recomendación:** Investigar con prioridad alta (validación antes de cualquier acción)

## Tesis de trabajo (no confirmada)
> «En una revisión de configuración, Andrea comenta que la tasa registrada parece coincidir con el valor mensual informado en la ficha comercial.» — **[F01.2]**

## Hechos confirmados en fuentes
> «En el canal Web de créditos, el sistema espera una tasa anual de seguro y calcula internamente su equivalente mensual.» — **[F01.1]**
> «Para el producto Crédito Flexible, la tasa de referencia aprobada se expresa anualmente.» — **[F02.1]**
> «La parametrización por canal debe recibir el dato anual; la mensualización la ejecuta el motor de cobros.» — **[F02.2]**
> «En la sesión de certificación se indicó que la tabla de configuración por canal admite un campo rate_input y que el motor aplica una conversión anual-a-mensual.» — **[F03.1]**

## Hipótesis
> «En una revisión de configuración, Andrea comenta que la tasa registrada parece coincidir con el valor mensual informado en la ficha comercial.» — **[F01.2]**
> «Operaciones detectó que la prima promedio registrada para algunos créditos originados en Web es inferior a la de operaciones aparentemente similares.» — **[F04.1]**
> «La alerta se considera preliminar.» — **[F04.6]**

## Datos faltantes / pendientes
> «No se ha confirmado si esa parametrización está activa en producción.» — **[F01.3]**
> «En el hilo también se menciona que la pantalla de administración permite copiar configuraciones entre canales, pero nadie confirma si la captura corresponde a producción o certificación.» — **[F01.4]**
> «Un segundo participante advierte que una comparación de primas sin controlar el saldo asegurado podría inducir a error.» — **[F01.5]**
> «La tasa y la vigencia exactas deben verificarse en la tabla de parámetros autorizada.» — **[F02.3]**
> «El equipo solicita contrastar el valor cargado para Web con el de otros canales antes de concluir que hay un defecto.» — **[F03.2]**
> «La comparación no está ajustada por saldos, fechas ni elegibilidad.» — **[F04.2]**
> «Se solicita análisis transaccional para confirmar una eventual desviación.» — **[F04.3]**
> «El archivo adjunto citado en el correo no se encuentra en esta carpeta.» — **[F04.4]**
> «El equipo de operaciones no dispone todavía de una muestra de operaciones con idéntico saldo y periodo de cobertura.» — **[F04.5]**

## Consulta a herramienta local
- `consultar_parametros.py 'Credito Flexible' 'Web' 'rate_input'` → Web: valor=pendiente_de_validar, estado=sin_confirmacion, esperado=anual, rev=2026-09-06 · registro anterior a F03, F04: contrastar
- `consultar_parametros.py 'Credito Flexible' 'Sucursal' 'rate_input'` → Sucursal: valor=anual, estado=vigente, esperado=anual, rev=2026-09-06 · registro anterior a F03, F04: contrastar
- ⚠ Herramienta: _Registro simulado; contrastar con fuentes y no inferir leakage cuantificado_

## Lo que NO afirmo
- No cuantifico pérdida/fuga: la comparación no controla saldo, periodo ni elegibilidad.
- No afirmo estado productivo: la evidencia no distingue producción de certificación/demo.

## Próximos pasos (derivados de fuentes)
- La tasa y la vigencia exactas deben verificarse en la tabla de parámetros autorizada. [F02.3]
- El equipo solicita contrastar el valor cargado para Web con el de otros canales antes de concluir que hay un defecto. [F03.2]
- Se solicita análisis transaccional para confirmar una eventual desviación. [F04.3]

## Fuentes
- **F01** · 2026-09-03 · Teams · Canales Digitales · Parametrización desgravamen web
- **F02** · 2026-09-05 · Ficha técnica · Seguros · Definición de tasa de desgravamen
- **F03** · 2026-09-07 · Acta de reunión · Tecnología · Revisión de canal Web
- **F04** · 2026-09-09 · Correo · Operaciones · Consulta de cobros Web
