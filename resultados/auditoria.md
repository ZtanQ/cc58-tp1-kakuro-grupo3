# Auditoría contra el enunciado (Topicos_CC-4.pdf)

Fecha: 30/09/2026 (actualizada con las pruebas de `tests/`). Código en `src/kakuro/`, evaluado con `scripts/evaluar.py` (Tesseract 5.3.4) sobre las 58 imágenes de `data/original/` y aparte sobre `data/rechazo/`.

**Estados:**
- **cumple**: el código lo hace y hay una medición o prueba que lo muestra;
- **parcial**: está hecho, pero le falta algo para cumplir del todo;
- **falta**: no está hecho. Es el caso del informe LaTeX, el video y el repositorio en GitHub, que no dependen del código.

## Resumen

| Bloque | Cumple | Parcial | Falta |
|---|---|---|---|
| Fase 1 — Visión e IA | 6 | 0 | 0 |
| Fase 2 — Constraint Programming | 6 | 0 | 0 |
| Fase 3 — Integración y visualización | 2 | 0 | 0 |
| Entregables | 1 | 1 | 2 |
| Rúbrica (20 puntos) | 7 filas (12 pts) | 1 fila (3 pts) | 1 fila (5 pts) |

Lo que falta para la entrega: **subir el repositorio a GitHub, el informe en LaTeX y el video**. Las 3 fases cumplen. Una fila de la rúbrica queda "parcial" y conviene reforzarla en el informe: restricciones globales (ver el final de la sección 3).

---

## 1. Fases del desarrollo

### Fase 1 — Visión computacional e IA

| Requisito | Dónde se cumple | Evidencia | Estado |
|---|---|---|---|
| Recibir una imagen `.jpg` o `.png` | `pipeline.leer_imagen`, `pipeline.resolver_imagen`, CLI `python -m kakuro.pipeline` | 58 imágenes: 32 `.png` y 26 `.jpg`; también acepta `.jpeg` (foto de rechazo). | cumple |
| Preprocesamiento: escala de grises, binarización, corrección de perspectiva | `tablero.rectificar_tablero` (grises, desenfoque, CLAHE, Canny, umbral adaptativo, `warpPerspective`), `tablero.candidatos_por_lineas` (respaldo con Hough), `celdas.normalizar_iluminacion`, `ocr.preparar_numero` (Otsu y adaptativo) | Grilla correcta en 58/58, incluidas 7 fotos inclinadas o muy inclinadas. | cumple |
| Segmentar la cuadrícula y las celdas | `cuadricula.proyecciones_lineas`, `cuadricula.detectar_cuadricula` (puntaje por cada n de 3 a 7), `celdas.recortar_celdas` | Tamaño correcto 58/58. Celdas blancas correctas 56/58 (31/31 digitales). | cumple |
| Clasificar el contenido de cada celda (blanca / pista y dígitos) | `celdas.segmentar_y_clasificar` y `celdas.tiene_diagonal`; `ocr.leer_pista` (Tesseract LSTM, hasta 8 binarizaciones y votación); `ocr.filtrar_bandas` para moiré | OCR con el primer candidato correcto: 487/503 (97%). Digitales 261/261 (100%), papel 133/142 (94%), pantalla 93/100 (93%). | cumple |
| Generar una estructura de datos (JSON) con el estado inicial | `estructura.exportar_json`, CLI `--json`, `evaluar.py` → `resultados/json/` | JSON exportado igual al ground truth en celdas y pistas: 31/31 digitales (50/58 en total; las 8 diferencias son fotos con algún error de lectura). | cumple |
| Modelo preentrenado debidamente referenciado | Tesseract OCR (motor LSTM, `--oem 1`), citado en `README.md` | Versión fijada y medida: 5.3.4. Falta citarlo también en el informe. | cumple |

### Fase 2 — Constraint Programming

| Requisito | Dónde se cumple | Evidencia | Estado |
|---|---|---|---|
| Usar una herramienta de CP | OR-Tools CP-SAT 9.15 (`modelo_cp.resolver_csp`) | 55 de 58 imágenes llegan a `OPTIMAL`. | cumple |
| Definición clara de variables y dominios | `modelo_cp.crear_variables`: `x_f_c ∈ {1..9}` por celda blanca; `s_i` por grupo con dominio = sumas candidatas. `modelo_cp.dominios_pistas`: rango válido `[L(L+1)/2, L(19−L)/2]` y costo por ranking del OCR o por confusión de dígitos | Documentado en los docstrings de `modelo_cp.py` y en `config.py` (`DIGITO_MIN/MAX`, `COSTO_CONFUSION`). | cumple |
| Restricciones binarias y globales (`alldifferent`, `sum`) | `modelo_cp.agregar_restricciones`: `AddAllDifferent` y suma lineal `Σ x = s_i` por grupo. Binarias reificadas `s_i = v` / `s_i ≠ v` en `definir_objetivo` | Las 54 soluciones correctas cumplen sumas y no repiten dígitos (comparadas con el ground truth, que también se validó). | cumple |
| Modelo parametrizado (nada "hardcodeado") | El modelo se arma desde los grupos detectados (`estructura.construir_grupos`); no hay tamaños ni pistas fijas | Resuelve tableros de n = 3, 4, 5, 6 y 7 (14, 11, 16, 2 y 15 imágenes). | cumple |
| Resolver de manera óptima | `definir_objetivo`: minimiza el costo total de corregir lecturas; semilla fija y un hilo (`config.SEMILLA`, `config.HILOS`) | Todas las soluciones presentadas son `OPTIMAL`. El resultado es reproducible: notebook vs `src/` da 0 diferencias en 59 imágenes. | cumple |
| No inventar pistas | `resolver_csp` devuelve `PISTAS_SIN_LECTURA` o `PISTAS_FUERA_DE_RANGO` sin llamar al solver | 3 fotos terminan sin solución en vez de inventar (`INFEASIBLE`, `PISTAS_SIN_LECTURA`, `PISTAS_FUERA_DE_RANGO`). | cumple |

### Fase 3 — Integración y visualización

| Requisito | Dónde se cumple | Evidencia | Estado |
|---|---|---|---|
| La salida de la Fase 1 entra a la Fase 2 de forma automática | `pipeline.procesar_imagen` → `intentar_resolver` (lee pistas → grupos → CP), con reintento automático con filtro de bandas | `evaluar.py` procesa las 58 imágenes sin intervención; 4 usan el reintento sin que nadie lo active. | cumple |
| Mostrar la solución de forma visual y comprensible | `visualizacion.dibujar_solucion` (dígitos centrados en cada celda); `notebooks/demo_colab.ipynb` muestra la original y la solución lado a lado | `resultados/soluciones/` (55 imágenes). El notebook se ejecutó de punta a punta con una digital y una foto de papel. Los dígitos se dibujan sobre la imagen **rectificada**, no sobre la foto original sin corregir; el enunciado acepta cualquiera de las dos. | cumple |

---

## 2. Entregables

| Entregable | Dónde se cumple | Evidencia | Estado |
|---|---|---|---|
| 1. Código fuente en GitHub, ordenado y comentado, con `README.md` (instalación exacta y ejecución) | `src/kakuro/` (9 módulos), `README.md`, `requirements.txt` con versiones fijas | 72/72 funciones y clases de `src/` y `scripts/` con docstring; umbrales en `config.py`; 72 pruebas con pytest que pasan; historial en git local con un commit por cambio. **Falta crear el repositorio en GitHub y subirlo.** | parcial |
| 2. Dataset de al menos 10 imágenes en distintas condiciones (iluminación, ángulos ligeros, digitales e impresas) | `data/original/`, `data/ground_truth/`, `data/rechazo/`, `data/CAMBIOS.md` | 58 imágenes: 31 digitales, 19 fotos de papel impreso (frente, inclinada, muy inclinada, luz tenue, sombra, borrosa) y 8 de pantalla (frente, inclinada, muy inclinada, luz tenue, reflejo, moiré). Más 1 de rechazo. Cada una con su JSON. | cumple |
| 3. Informe técnico PDF (IEEE o similar): pipeline de visión y métricas de error; modelo formal de CP; complejidad y tiempos del solver | Datos listos en `resultados/resumen.md` y en esta auditoría; el detalle por imagen lo genera `scripts/evaluar.py` en `resultados/metricas.csv` | Tiempos del solver por tamaño: n=3 → 4 ms de promedio, n=7 → 27 ms; hasta 1620 ramas y 44 conflictos. Falta escribir el informe, incluido el **análisis de complejidad**, que todavía no está redactado en ningún lado. | falta |
| 4. Video de máximo 5 minutos con los 3 integrantes | `notebooks/demo_colab.ipynb` sirve para la demostración en vivo | — | falta |

---

## 3. Rúbrica

| Criterio | Pts | Dónde se cumple | Evidencia | Estado |
|---|---|---|---|---|
| Precisión en la detección de la cuadrícula, números y símbolos | 3 | `tablero`, `cuadricula`, `celdas`, `ocr` | Grilla 58/58; celdas 56/58; OCR 97% (100% en digitales); solución 54/58. | cumple |
| Bajo diferentes condiciones de imagen | 1 | Mismo pipeline + reintento con `filtrar_bandas` | Foto papel 16/19, foto pantalla 7/8, oclusión rechazada (1/1). Fallan: muy inclinada, 2 con sombra y la borrosa. | cumple |
| Correcta formulación del problema matemático | 3 | `modelo_cp.py` | 31/31 digitales correctas; el modelo nunca da una solución que viole sumas o `AllDifferent`. **Para el informe:** escribir el modelo formal (variables, dominios, restricciones, objetivo). | cumple |
| Uso eficiente de restricciones globales | 3 | `AddAllDifferent` + suma lineal por grupo | Funciona y es rápido (≤ 60 ms). La restricción de tabla `AddAllowedAssignments` por (longitud, suma), que es la forma clásica y poda más, no está implementada; queda como propuesta que el equipo decide si aplicar. Un evaluador puede esperar más que `AllDifferent` + suma. | parcial |
| Uso eficiente de restricciones reificadas (o explicar por qué no) | 1 | `modelo_cp.definir_objetivo` (`OnlyEnforceIf`), explicado en su docstring | Son necesarias para cobrar un costo distinto por cada suma candidata con un objetivo lineal. Falta la explicación en el informe. | cumple |
| El puente entre la IA y el modelo CP funciona sin intervención manual | 1 | `pipeline.procesar_imagen` | 58 imágenes procesadas por `evaluar.py` sin intervención. | cumple |
| La solución se muestra visualmente de forma clara | 1 | `visualizacion.dibujar_solucion`, `notebooks/demo_colab.ipynb` | Original y solución lado a lado en el notebook; pistas ajustadas y tiempos impresos. | cumple |
| Código limpio, modularizado y con buenas prácticas | 2 | `src/kakuro/` (9 módulos por etapa), `config.py`, `scripts/` (evaluar, generar_resumen, verificar_ground_truth), `tests/`, `data/CAMBIOS.md` | Docstrings completos, sin números mágicos fuera de `config.py`, resultados reproducibles (semilla fija, versiones fijas), migración verificada imagen por imagen. **`python -m pytest tests`: 72 pruebas pasan** (en Windows y en el contenedor Ubuntu 24.04): modelo CP (3×3 resuelto, `INFEASIBLE`, `PISTAS_SIN_LECTURA`), `construir_grupos` (grupo de 1 celda, cobertura incompleta), `exportar_json` (formato del ground truth) y los 58 JSON del dataset. | cumple |
| Informe técnico claro, en LaTeX y con formato de artículo | 5 | — | No depende del código. | falta |

**Por qué queda una fila "parcial":**
- **Restricciones globales:** la mejora está identificada (restricción de tabla) y el equipo decide si aplicarla. Si no se aplica, el informe debería justificar por qué `AllDifferent` + suma alcanza (≤ 60 ms en 7×7).
- **Buenas prácticas pasó a "cumple"** con las pruebas de `tests/`. Los tests no cubren visión ni OCR, que los mide `scripts/evaluar.py`. El repositorio público se cuenta en el entregable 1.

---

## 4. Riesgos que conviene mencionar en el informe

- **Un error silencioso:** `L_kakuro_05x05_clasico_01_papel_borrosa` (309×307 px) se presenta como resuelta y es incorrecta. Hay propuestas para detectarlo: resolución mínima de celda y chequeo de unicidad.
- **Dependencia de la versión de Tesseract:** las métricas se midieron con 5.3.4. Otra versión puede cambiar el OCR.
- **Tiempo de OCR:** domina el tiempo total (de 5 a 15 s por imagen en Docker, hasta ~40 s con reintento). El solver tarda milisegundos.
