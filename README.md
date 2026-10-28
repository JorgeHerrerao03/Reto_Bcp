# Revenue Signals Agent · Reto BCP

Agente que lee fuentes internas desordenadas (correos, Teams, actas) y:

- detecta **señales con potencial económico**;
- separa **hechos, hipótesis y faltantes**, citando cada oración (`[F04.3]`);
- consulta la herramienta local **solo cuando tiene sentido** y deja registro de cada decisión;
- produce un **Opportunity Brief** por señal, con un apartado de **"Lo que NO afirmo"**;
- incorpora evidencia nueva en vivo y explica **qué cambió y por qué**.

Python ≥ 3.9 · **cero dependencias** · funciona offline · Claude es opcional.

---

## 1. Inicio rápido (Windows)

| Opción | Cómo |
|---|---|
| **Doble clic** | `Iniciar_RevenueSignals.bat` abre la app en el navegador |
| **Ejecutable .exe** | Ejecuta `build_exe.bat` una vez; genera `RevenueSignals.exe`, que se abre con doble clic. Debe quedar junto a `paquete\` y `demo\` |
| **Terminal** | `python -m rsa app` |

La app corre en `http://127.0.0.1:8765` y escucha solo en tu PC.

## 2. Qué puedes hacer en la app

| Función | Detalle |
|---|---|
| **＋ Añadir fuente** | Arrastras un `.md`, `.txt` o `.docx`, o pegas texto. El ID y la fecha se autocompletan |
| **Previsualizar impacto** | Muestra qué cambiaría *antes* de incorporar: scores, refutaciones y la clasificación de cada oración. No guarda nada |
| **Segunda opinión de Claude** | Claude propone relaciones (refuta, confirma, resuelve) entre la fuente nueva y la evidencia existente. Solo se aceptan IDs que existen |
| **Máquina del tiempo** | v1 → vN, con ▲▼ por señal, transiciones (hipótesis → refutada) y un resumen de "qué cambió" |
| **Deshacer última** | Retira la última fuente incorporada |
| **Demos** | Contradice (F19), confirma (F20) y ruido (F21), para ensayar la entrevista |
| **Preguntar a las fuentes** | Búsqueda por oración. Con Claude, redacta la respuesta citando solo esa evidencia |
| **Grafo de evidencia** | Fuentes por señal con fecha, aristas *refuta* / *resuelve* y consultas a la herramienta |
| **Matriz impacto × evidencia** | Cuadrantes: actuar, investigar, monitorear |
| **¿Y si cambio los pesos?** | Sliders que re-rankean en vivo, para discutir supuestos de negocio |
| **Brief .md / Imprimir PDF** | Exporta el informe de la señal |
| **Claude ⚙** | Configura la API key, prueba la conexión y genera resúmenes ejecutivos |

## 3. Claude (opcional)

1. Crea una API key en **console.anthropic.com → API Keys** y carga créditos. Una suscripción Claude Pro/Max **no** incluye acceso a la API.
2. Configúrala de una de estas formas. La key se guarda en `.env`, que está excluido de git.
   - En la app: botón **Claude ⚙**, luego Guardar y Probar conexión.
   - Por terminal: `python -m rsa config --key sk-ant-...`
   - Copiando `.env.example` como `.env`.
3. Modelo por defecto: `claude-haiku-5-5`. Se cambia con `RSA_MODEL`.

| Uso de Claude | Guardrail |
|---|---|
| Resumen ejecutivo por señal | Cada `[Fxx.n]` debe existir; si aparece una cifra inventada o una cita inválida, el resumen se descarta |
| Preguntar a las fuentes | Solo puede usar la evidencia recuperada; se marca si las citas son válidas |
| Segunda opinión sobre una fuente nueva | Solo relaciones con IDs reales; es una sugerencia, no cambia el análisis determinístico |

**Costo** (Haiku 5.5: USD 0.10 / 0.50 por millón de tokens de entrada / salida):
- un resumen cuesta ≈ USD 0.0002;
- una corrida completa con 4 señales cuesta < USD 0.001.

Tokens, costo y latencia de cada llamada quedan en la traza.

## 4. GitHub: reporte que se actualiza solo

El reporte público vive en `docs/index.html` (GitHub Pages). Para agregar evidencia sin instalar nada:

1. En GitHub, entra a `fuentes_nuevas/` → **Add file → Create new file**. Usa como base `fuentes_nuevas/PLANTILLA.txt` y guarda el archivo como `F19_algo.md`.
2. Haz **Commit**. La GitHub Action `Actualizar reporte`:
   - corre los tests;
   - reconstruye todo e incorpora cada `.md` en orden de fecha;
   - publica `docs/index.html`.
3. En 1–2 minutos, el link de Pages muestra la nueva versión con su máquina del tiempo.

Si configuras el secret `ANTHROPIC_API_KEY` (Settings → Secrets → Actions), la Action agrega también los resúmenes de Claude.

La versión publicada es de solo lectura: tiene ranking, briefs, grafo, matriz, pesos y búsqueda. Añadir fuentes desde la interfaz requiere la app local.

## 5. Línea de comandos

```bash
python -m rsa run --reset                 # ingesta de las 18 fuentes
python -m rsa senales                     # ranking
python -m rsa investigar S1               # brief + traza
python -m rsa incorporar nueva.md         # agrega una fuente y muestra el diff
python -m rsa deshacer                    # retira la última fuente incorporada
python -m rsa preguntar "¿hay piloto productivo?"  [--llm antes del comando]
python -m rsa consultar "Credito Flexible" Web rate_input
python -m rsa sync fuentes_nuevas         # lo que corre la Action
python -m rsa demo --caso todos
python -m unittest discover -s tests -t . -v      # 17 tests
```

## 6. Arquitectura

```
ingesta (CSV + md, sha1) → relevancia (léxico económico / declaración de no-impacto)
 → vinculación contextual → agrupamiento (TF-IDF + palanca) → afirmaciones por oración
 → contradicciones (corrección refuta hipótesis / resuelve faltante) → política de herramienta
 → score → guardrails "Lo que NO afirmo" → briefs + traza + diff + reporte
```

| Módulo | Rol |
|---|---|
| `corpus.py` · `convert.py` | Ingesta, oraciones con ID estable, conversión de .md/.txt/.docx/texto |
| `lexicon.py` | **Único lugar con conocimiento de dominio** (cues, palancas, pesos, guardrails) |
| `analyze.py` | Relevancia, clustering, clasificación, contradicciones, score |
| `tools.py` | Política de consulta. La herramienta se ejecuta sin modificar, en proceso |
| `engine.py` | Estado versionado, incorporar, preview, deshacer, sync, diff |
| `search.py` · `llm.py` | Recuperación por oración · capa Claude con validación de citas |
| `server.py` · `report.py` | App local (stdlib) · HTML único que sirve tanto para la app como para la versión estática |

**Score:** `100·(0.45·impacto + 0.30·evidencia + 0.25·urgencia) − 6·refutaciones (máx. 18)`. Los pesos se pueden discutir en vivo con los sliders.

| Determinístico | Agentic |
|---|---|
| Ingesta, clasificación, contradicciones, score, diff | Decidir si consultar la herramienta y con qué parámetros, con el motivo en el log (incluidas las omisiones) |
| Mismo input, mismo output; todo auditable | Claude (opcional): resumen, preguntas, segunda opinión, siempre con citas validadas |

## 7. Resultado sobre el paquete

| Señal | Fuentes | Clave |
|---|---|---|
| S1 Desviación en cobro de seguro | F01–F04 | Herramienta: Web `pendiente_de_validar` contra Sucursal `vigente`. No se cuantifica fuga |
| S2 Comisiones de baja frecuencia | F17–F18 | No se recomienda eliminar sin conciliar ni medir materialidad |
| S3 Exoneración de membresía | F05–F07 | Retención contra ingreso queda como hipótesis |
| S4 Día de pago | F08–F12 | F12 refuta a F11 (maqueta ≠ piloto); la herramienta se omite porque falta el producto |
| Ruido | F13–F16 | Cada una se descarta citando su declaración de no-impacto |

## 8. Limitaciones

- La clasificación y las contradicciones son heurísticas léxicas. Ante una redacción muy distinta se amplía `lexicon.py`, o se usa la segunda opinión de Claude.
- Un documento que mezcla dos palancas se asigna a la dominante.
- Los pesos de impacto son supuestos de negocio explícitos, no aprendidos.
