# Revenue Signals Agent · Reto BCP

Agente que lee fuentes internas desordenadas (correos, Teams, actas) y:

- detecta **señales con potencial económico**;
- separa **hechos, hipótesis y faltantes**, citando cada oración (`[F04.3]`);
- consulta la herramienta local **solo cuando tiene sentido** y deja registro de cada decisión;
- produce un **Opportunity Brief** por señal, con un apartado de **"Lo que NO afirmo"**;
- incorpora evidencia nueva en vivo y explica **qué cambió y por qué**.

Python ≥ 3.9 · **cero dependencias** · **Claude decide y las reglas auditan** · si no hay API, funciona offline solo con reglas.

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
| **＋ Añadir fuente** | Arrastras un `.md`, `.txt`, `.docx` (incluye tablas), `.xlsx`, `.csv`, `.pdf` o una imagen, o pegas texto. El ID y la fecha se autocompletan |
| **Previsualizar impacto** | Muestra qué cambiaría *antes* de incorporar: scores, refutaciones y la clasificación de cada oración. No guarda nada |
| **Segunda opinión de Claude** | Claude propone relaciones (refuta, confirma, resuelve) entre la fuente nueva y la evidencia existente. Solo se aceptan IDs que existen |
| **Máquina del tiempo** | v1 → vN, con ▲▼ por señal, transiciones (hipótesis → refutada) y un resumen de "qué cambió" |
| **Deshacer última** | Retira la última fuente incorporada |
| **Demos** | Contradice (F19), confirma (F20) y ruido (F21), para ensayar la entrevista |
| **Preguntar a las fuentes** | Búsqueda por oración. Con Claude, redacta la respuesta citando solo esa evidencia |
| **Grafo de evidencia** | Fuentes por señal con fecha, aristas *refuta* / *resuelve* y consultas a la herramienta |
| **Matriz impacto × evidencia** | Cuadrantes: actuar, investigar, monitorear |
| **¿Y si cambio los pesos?** | Sliders que re-rankean en vivo, para discutir supuestos de negocio |
| **⬇ Word / .md / Imprimir PDF** | Opportunity Brief en Word (.docx) con membrete; el logo solo se incluye si existe `marca/logo.png` local |
| **Claude ⚙** | Configura la API key, prueba la conexión y genera resúmenes ejecutivos |

## 3. Motor Claude-first (las reglas auditan)

Con API key configurada, **Claude decide siempre**: entiende español informal, spanglish e inglés. Sin key o si la API falla, el sistema usa automáticamente el motor de reglas y lo indica en pantalla.

| Paso | Quién decide | Quién audita |
|---|---|---|
| ¿Es ruido o tiene relevancia económica? | Claude | Reglas (léxico) |
| ¿A qué señal pertenece? | Claude (palanca, incluso si es una palanca nueva) | TF-IDF |
| Tipo de cada oración: hecho / hipótesis / faltante / corrección / advertencia | Claude, con su razón | Reglas: ⚠ si discrepan |
| Qué refuta, resuelve o **confirma** a qué | Claude | Reglas: las disputas van al comité |
| Producto / canal / parámetro para la herramienta | Reglas; Claude como respaldo, solo valores del catálogo | — |
| Score 0–100 | **Fórmula determinística** sobre el resultado final | — |
| Resumen ejecutivo y cautelas ("Lo que NO afirmo") | Claude + reglas | Citas validadas |

**Comité de verificación (debate).** Cuando Claude y las reglas discrepan sobre la relevancia o sobre una refutación o resolución, se arma un comité: una postura SÍ y una postura NO en paralelo, y un juez que decide citando evidencia. El tope es de 3 comités por análisis, y el veredicto se aplica y queda visible en la pestaña Resumen.

**Guardrails.**
- JSON con formato fijo; la reproducibilidad se asegura con la caché por contenido.
- Se descartan los IDs que no existan.
- Las relaciones solo pueden ir de una fuente posterior a una anterior.
- Se rechaza cualquier cifra inventada.
- Caché por contenido en `.cache/`: repetir un análisis no vuelve a llamar a la API.

**Configurar.** En la app: ⋯ → Conectar Claude, o `python -m rsa config --key sk-ant-...`. Necesitas una API key de console.anthropic.com; una suscripción Pro/Max no incluye API. Para forzar el modo reglas: `python -m rsa --solo-reglas app` o `RSA_MODO=reglas`.

**Costo.** Con Haiku 5.5 (USD 0.10 / 0.50 por MTok):
- El primer análisis de las 18 fuentes cuesta unas 25 llamadas, menos de USD 0.01, y tarda 20–40 s.
- Cada fuente nueva cuesta 2 a 6 llamadas, unos 3–15 s.
- Lo que ya está en caché cuesta USD 0.

**Casos difíciles para ensayar** (`demo/dificiles/`). Muestran dónde fallan las reglas y por qué Claude decide:

| Archivo | Solo reglas | Con Claude (esperado) |
|---|---|---|
| `F22_fee_en_ingles.md` | Crea una señal absurda ("the, onboarding, fee") | Va a Comisiones; "Pending…" es faltante |
| `F23_correccion_informal.md` | No ve la corrección; S1 sube | Refuta F01.2 ("no era así… era QA") |
| `F24_aprobacion_en_ingles.md` | La descarta como ruido | Va a Exoneración; resuelve "sin aprobación formal" (F05.2) |

## 3b. Adjuntos: Excel, CSV, imágenes y PDF

| Formato | Cómo se lee | Requiere Claude |
|---|---|---|
| `.xlsx` / `.csv` / `.tsv` / tablas en `.docx` | Lector propio (stdlib). Cada fila es una oración citable (`F19.8` = fila 1) | No |
| Imagen (`.png`, `.jpg`, `.webp`) / `.pdf` | Claude transcribe literalmente, con las tablas en formato `Fila n · col: valor` | Sí |

- **Las cifras las calcula el código, nunca el LLM:** totales, promedios, mínimos, máximos y promedios por grupo (por ejemplo, por canal), con razón y diferencia porcentual entre dos grupos. Se insertan como oraciones `Cálculo (código) · …` citables.
- Con datos tabulados, "No cuantifico" se reemplaza por **"Cuantifico solo sobre la muestra tabulada…; no extrapolo a toda la cartera"**.
- Claude solo puede usar en sus resúmenes cifras que aparezcan literalmente en la evidencia; si usa otra, el resumen se descarta.
- Las filas de una tabla no inflan el score. Cuentan como evidencia, no como afirmaciones independientes.

**Casos de prueba** (`demo/adjuntos/`, datos ficticios):
- `adjunto_F04_muestra.xlsx` / `.csv`: el "archivo adjunto" que faltaba en F04. Son 40 operaciones en pares con el mismo saldo; la prima Web es el **8,29 %** de la de Sucursal (≈ 1/12, que es lo esperable si se cargó la tasa mensual como anual). Con reglas resuelve F04.5. Con Claude debería resolver además F04.4 y confirmar F01.2.
- `captura_parametros_produccion.png`: captura de "Producción" con rate_input Web 0.00054 contra Sucursal/App 0.0065. Requiere Claude.

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
python -m unittest discover -s tests -t . -v      # 24 tests (núcleo en modo reglas + modo Claude con stub)
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

| Determinístico | Agentic (Claude) |
|---|---|
| Ingesta, IDs por oración, score, diff, caché, validaciones | Relevancia, agrupamiento, tipo de oración, relaciones, cautelas, resumen |
| Reglas como auditor y respaldo automático | Comité SÍ/NO + juez solo ante discrepancias |

## 7. Resultado sobre el paquete

| Señal | Fuentes | Clave |
|---|---|---|
| S1 Desviación en cobro de seguro | F01–F04 | Herramienta: Web `pendiente_de_validar` contra Sucursal `vigente`. No se cuantifica fuga |
| S2 Comisiones y tarifas | F17–F18 | No se recomienda eliminar sin conciliar ni medir materialidad |
| S3 Exoneración de membresía | F05–F07 | Retención contra ingreso queda como hipótesis |
| S4 Día de pago | F08–F12 | F12 refuta a F11 (maqueta ≠ piloto); la herramienta se omite porque falta el producto |
| Ruido | F13–F16 | Cada una se descarta citando su declaración de no-impacto |

## 8. Limitaciones

- Claude no es 100 % reproducible: se mitiga con caché por contenido y auditoría de las reglas. Las discrepancias quedan visibles.
- Sin API, el respaldo vuelve a las heurísticas léxicas, que se amplían en `lexicon.py`.
- Un documento que mezcla dos palancas se asigna a la dominante.
- Los pesos de impacto son supuestos de negocio explícitos, no aprendidos.
