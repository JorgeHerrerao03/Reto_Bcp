# Traza de investigación · S1 · Posible desviación en cobro de seguro

| # | Acción | Detalle |
|---|---|---|
| 1 | ingestar | {'n_fuentes': 18, 'fuentes': ['F01:6ff8fb108d', 'F02:0cbb307478', 'F03:fcdafab3cf', 'F04:a87754f763', 'F05:1a6a873182', 'F06:7a4b159178', 'F07:31d5a8b89e', 'F08:100a180436', 'F09:78708131ff', 'F10:0a58333f67', 'F11:3af9cf9be7', 'F12:2a7a389cb8', 'F13:14698d6fed', 'F14:3ab09b8e71', 'F15:fe2381dd82', 'F16:c513ff3f79', 'F17:9b8efea897', 'F18:a76fccaed2']} |
| 2 | clasificar_relevancia | {'motor': 'reglas', 'relevantes': ['F01', 'F02', 'F03', 'F04', 'F05', 'F06', 'F07', 'F08', 'F09', 'F10', 'F11', 'F12', 'F17', 'F18'], 'descartadas': ['F13', 'F14', 'F15', 'F16'], 'discrepancias_reglas': []} |
| 3 | agrupar_fuentes | grupo de la señal: ['F01', 'F02', 'F03', 'F04'] |
| 4 | consulta_herramienta | args=['Credito Flexible', 'Web', 'rate_input'] · motivo: producto/canal/parámetro explícitos en fuentes · encontrado=True · [{'producto': 'Credito Flexible', 'canal': 'Web', 'parametro': 'rate_input', 'unidad_esperada': 'anual', 'valor_configurado': 'pendiente_de_validar', 'estado_produccion': 'sin_confirmacion', 'ultima_revision': '2026-09-06'}] · 2 ms |
| 5 | consulta_herramienta | args=['Credito Flexible', 'Sucursal', 'rate_input'] · motivo: contraste entre canales solicitado en fuentes · encontrado=True · [{'producto': 'Credito Flexible', 'canal': 'Sucursal', 'parametro': 'rate_input', 'unidad_esperada': 'anual', 'valor_configurado': 'anual', 'estado_produccion': 'vigente', 'ultima_revision': '2026-09-06'}] · 0 ms |

**Fuentes consultadas:** F01, F02, F03, F04
**Aspectos no resueltos:**
- No se ha confirmado si esa parametrización está activa en producción. [F01.3]
- En el hilo también se menciona que la pantalla de administración permite copiar configuraciones entre canales, pero nadie confirma si la captura corresponde a producción o certificación. [F01.4]
- Un segundo participante advierte que una comparación de primas sin controlar el saldo asegurado podría inducir a error. [F01.5]
- La tasa y la vigencia exactas deben verificarse en la tabla de parámetros autorizada. [F02.3]
- El equipo solicita contrastar el valor cargado para Web con el de otros canales antes de concluir que hay un defecto. [F03.2]
- La comparación no está ajustada por saldos, fechas ni elegibilidad. [F04.2]
- Se solicita análisis transaccional para confirmar una eventual desviación. [F04.3]
- El archivo adjunto citado en el correo no se encuentra en esta carpeta. [F04.4]
- El equipo de operaciones no dispone todavía de una muestra de operaciones con idéntico saldo y periodo de cobertura. [F04.5]
