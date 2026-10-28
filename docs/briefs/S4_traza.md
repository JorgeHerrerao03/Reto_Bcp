# Traza de investigación · S4 · Cambio de calendario / día de pago

| # | Acción | Detalle |
|---|---|---|
| 1 | ingestar | {'n_fuentes': 18, 'fuentes': ['F01:6ff8fb108d', 'F02:0cbb307478', 'F03:fcdafab3cf', 'F04:a87754f763', 'F05:1a6a873182', 'F06:7a4b159178', 'F07:31d5a8b89e', 'F08:100a180436', 'F09:78708131ff', 'F10:0a58333f67', 'F11:3af9cf9be7', 'F12:2a7a389cb8', 'F13:14698d6fed', 'F14:3ab09b8e71', 'F15:fe2381dd82', 'F16:c513ff3f79', 'F17:9b8efea897', 'F18:a76fccaed2']} |
| 2 | clasificar_relevancia | {'nucleo_economico': ['F01', 'F02', 'F03', 'F04', 'F05', 'F06', 'F07', 'F08', 'F09', 'F17', 'F18'], 'ruido_explicito': ['F13', 'F14', 'F15', 'F16'], 'sin_lexico_economico': ['F10', 'F11', 'F12']} |
| 3 | vincular_contextuales | {'fuentes': {'F10': "vinculada por palanca 'Cambio de calendario / día de pago'", 'F11': "vinculada por palanca 'Cambio de calendario / día de pago'", 'F12': "vinculada por palanca 'Cambio de calendario / día de pago'"}} |
| 4 | agrupar_fuentes | grupo de la señal: ['F08', 'F09', 'F10', 'F11', 'F12'] |
| 5 | consulta_omitida | no inferible desde fuentes: producto |

**Fuentes consultadas:** F08, F09, F10, F11, F12
**Aspectos no resueltos:**
- Se desconoce el efecto sobre comportamiento de pago y costo operativo. [F08.3]
- La propuesta aún no incluye una simulación financiera ni un análisis de impacto en cliente. [F09.3]
- La muestra es pequeña y no representa a toda la cartera. [F10.2]
- La minuta no distingue ambos entornos. [F11.4]
