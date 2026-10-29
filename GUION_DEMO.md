# Guion de la demo (5 min) · app local

Antes de empezar: doble clic en `Iniciar_RevenueSignals.bat`. Mira la barra superior: dice **"Motor: Claude decide, reglas auditan"** o **"Motor: solo reglas"**, y si alguna etapa de Claude falló lo indica con ⚠. Las cifras (88.8 → 77.7) son las del modo reglas; con Claude pueden variar algo, así que cita las que veas en pantalla.

| Tiempo | Acción en la app | Qué debe quedar probado |
|---|---|---|
| 0:00–0:30 | Pantalla inicial | 18 fuentes → 4 señales y 4 descartadas como ruido, y bajo qué supuestos se prioriza |
| 0:30–1:30 | S1 → Resumen (tarjeta Brief estratégico) | Lo que sabemos (observación de Operaciones, atribuida), lo que creemos (la causa: tasa mensual cargada como anual) y lo que falta. **Lo que NO afirmo**: no cuantifico la fuga |
| 1:30–2:10 | Consulta a la herramienta · pestaña Traza | Por qué se consultó Web y luego Sucursal, con qué parámetros y por qué el resultado no cierra el caso. En S2/S3/S4 la consulta se omite y queda el motivo |
| 2:10–3:30 | **＋ Añadir fuente** → `demo/F19_contradice.md` → **Previsualizar** → **Incorporar** | Cambia la conclusión: la tarjeta muestra **"Lo que cambió con la nueva evidencia"** (Tecnología declara… deja sin efecto F01.2 y resuelve F01.3/F01.4) y la cautela pasa a "Actualizado por F19". Sigue pendiente la muestra transaccional |
| 3:30–4:20 | S4 → Grafo y brief | F12 (maqueta) refuta F11 (piloto). Aunque Claude no lo vea, la corrección explícita de las reglas se conserva y queda marcada. Cada conclusión abre su oración |
| 4:20–5:00 | Arquitectura y límites | Qué decide el código (score, cálculos, validación de IDs y cifras) y qué interpreta Claude; comportamiento sin red; costo observado en pantalla; siguiente paso |

## Entrevista: fuentes nuevas

1. **＋ Añadir fuente**: pegar el texto o arrastrar el archivo (.md, .txt, .docx, .xlsx, .csv, .pdf o imagen).
2. **Previsualizar**: leer "Contenido extraído", "Qué cambiaría" y "Cómo se clasificó cada oración" (razón de Claude, "⚠ reglas decían…" y comité si lo hubo).
3. **Incorporar** y explicar el diff. Si algo no convence, usar **Deshacer última**.
4. Si Claude no está disponible (red), la app avisa "Motor: solo reglas". Explicar el trade-off: las reglas son auditables pero de cobertura limitada; Claude entiende la redacción libre y las reglas lo auditan.

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

## Antes de la entrevista (checklist)

- [ ] Abrir la app y confirmar **"Motor: Claude decide, reglas auditan"** (o ensayar en modo reglas si la red bloquea la API).
- [ ] No reiniciar justo antes: la caché asegura los mismos números que ensayaste.
- [ ] Tener a mano `demo\adjuntos\adjunto_F04_muestra.xlsx` y `demo\dificiles\F23_correccion_informal.md`. GitHub Pages es opcional: no depender de él en la demo.
- [ ] Si reanalizaste o incorporaste en el ensayo: **Deshacer última** (funciona también tras re-analizar) o ⋯ → Reset.
- [ ] Hotspot del celular como respaldo de red.
