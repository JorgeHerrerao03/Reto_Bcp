# Guion de la demo (5 min) · app local

Antes de empezar: doble clic en `Iniciar_RevenueSignals.bat` y luego **Reiniciar**.

| Tiempo | Acción en la app | Mensaje |
|---|---|---|
| 0:00–0:30 | Pantalla inicial | 18 fuentes → 4 señales y 4 descartadas como ruido. Determinístico, reproducible y sin internet |
| 0:30–1:30 | S1 → Opportunity Brief | Hechos, hipótesis y faltantes con cita por oración. **Lo que NO afirmo**: no cuantifico la fuga, no afirmo estado productivo |
| 1:30–2:00 | Brief → herramienta · pestaña Traza | Consulté Web y luego Sucursal porque F03 pide contrastar canales. En S3/S4 la consulta se omite y queda el motivo |
| 2:00–2:30 | S4 → Grafo | F12 refuta F11: arista roja y penalización en el score |
| 2:30–3:45 | **＋ Añadir fuente** → arrastrar `demo/F19_contradice.md` → **Previsualizar** → **Incorporar** | Antes de guardar se ve el impacto. Después, S1 baja 88.8 → 77.7: F01.2 queda refutada y F01.3/F01.4 resueltas. Comparar v1 ↔ v2 en la máquina del tiempo |
| 3:45–4:20 | Matriz · ¿Y si cambio los pesos? | Los pesos son supuestos de negocio explícitos y se pueden discutir en vivo |
| 4:20–5:00 | Preguntar a las fuentes (con Claude) · link de GitHub Pages | Claude solo responde con evidencia citada. El reporte público se regenera solo al subir una fuente al repo |

## Entrevista: fuentes nuevas

1. **＋ Añadir fuente**: pegar el texto o arrastrar el archivo, que puede ser .md, .txt o .docx.
2. **Previsualizar**: leer "Qué cambiaría" y "Cómo clasifiqué cada oración". Si hay key, activar la *Segunda opinión de Claude*.
3. **Incorporar** y explicar el diff. Si algo no convence, usar **Deshacer última**.
4. Si una contradicción no se detecta, mostrar `lexicon.py` (cues de CORRECCION) y explicar el trade-off entre la auditabilidad de las reglas y la cobertura del LLM.

## Si te traen lenguaje no normalizado (inglés, informal)

1. Primero muestra el contraste: corre en una terminal `python -m rsa --solo-reglas run --reset` y luego `python -m rsa --solo-reglas incorporar demo\dificiles\F23_correccion_informal.md`. Las reglas no ven la corrección.
2. En la app, que usa Claude: **＋ Añadir fuente** con el mismo archivo → **Previsualizar**. Muestra "Cómo se clasificó cada oración" (razón de Claude, "⚠ reglas decían…") y el **comité** si lo hubo.
3. Frase: *"Claude interpreta el lenguaje real, las reglas auditan, y si discrepan debate un comité con juez. El score es determinístico y todo cita la oración que lo sustenta."*

## Si te entregan "el adjunto de F04" (Excel, CSV o foto)

1. **＋ Añadir fuente** → arrastra el archivo → Título: "Adjunto F04: …", Área: Operaciones → **Previsualizar**.
2. Abre **"Contenido extraído"**: cada fila tiene su ID y los cálculos dicen *(código)*.
3. Frase: *"El agente no estima: el código calcula sobre la muestra y Claude solo interpreta cifras que ya existen en la evidencia. Por eso ahora sí cuantifica, pero solo sobre la muestra y sin extrapolar."*
4. Muestra cómo el faltante F04.4/F04.5 pasa a **resuelto** y el cambio de score.

Para ensayarlo: `demo\adjuntos\adjunto_F04_muestra.xlsx` y `demo\adjuntos\captura_parametros_produccion.png`.
