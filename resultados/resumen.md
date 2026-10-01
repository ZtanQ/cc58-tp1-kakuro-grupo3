# Resumen de métricas finales

Tablas para el informe. Se generan a partir de `resultados/metricas.csv` y `resultados/rechazo.csv`, que produce:

```bash
python scripts/evaluar.py --datos data --salida resultados/
```

Condiciones de la medición: 30/09/2026, `src/kakuro/` y `scripts/evaluar.py` del commit `9703e58`, Tesseract 5.3.4, OpenCV 5.0.0, OR-Tools 9.15.6755, Python 3.12, Docker (Ubuntu 24.04) sobre Windows 11. Todo se cuenta contra el JSON de `data/ground_truth/`; las fotos se comparan con el JSON de su imagen base.

## 1. Resultados por tipo de imagen

| Métrica | Digital | Foto papel | Foto pantalla | **Total** |
|---|---|---|---|---|
| Imágenes | 31 | 19 | 8 | 58 |
| Tamaño de grilla correcto | 31/31 | 19/19 | 8/8 | 58/58 |
| Celdas blancas correctas | 31/31 | 18/19 | 7/8 | 56/58 |
| OCR, pista correcta en primer candidato | 261/261 (100%) | 133/142 (94%) | 93/100 (93%) | 487/503 (97%) |
| JSON exportado = ground truth | 31/31 | 14/19 | 5/8 | 50/58 |
| **Solución correcta** | **31/31** | **16/19** | **7/8** | **54/58** |
| Incorrectas presentadas como correctas | 0 | 1 | 0 | 1 |
| Sin solución (el sistema no inventa) | 0 | 2 | 1 | 3 |
| Usaron el reintento de bandas | 0 | 2 | 2 | 4 |
| Pistas ajustadas por el solver | 0 | 4 | 2 | 6 |
| Tiempo promedio por imagen | 6.95 s | 9.15 s | 15.28 s | 8.82 s |
| Tiempo de visión promedio | 6.93 s | 9.14 s | 15.26 s | 8.80 s |
| Tiempo del solver (mín–máx) | 1–60 ms | 0–23 ms | 8–30 ms | 0–60 ms |

**Rechazo** (`data/rechazo/`, el acierto es no presentar solución): 1/1.
- `L_kakuro_07x07_clasico_01_papel_oclusion.jpeg`: estado `NO_EJECUTADO`, etapa `tablero`. Mensaje: "No se pudo localizar el tablero completo. Usa una foto nítida con sus cuatro bordes visibles."

Los tiempos dependen de la máquina. En Colab, el equipo midió ~3.4 s por imagen digital. En todos los casos casi todo el tiempo es OCR.

## 2. Fotos por condición

| Soporte | Condición | Fotos | Solución correcta | OCR primer candidato | Reintento |
|---|---|---|---|---|---|
| pantalla | frente | 2 | 2/2 | 24/24 (100%) | 0 |
| pantalla | inclinada | 2 | 2/2 | 23/24 (96%) | 0 |
| pantalla | luz_tenue | 1 | 1/1 | 8/8 (100%) | 0 |
| pantalla | moire | 1 | 1/1 | 7/8 (88%) | 1 |
| pantalla | muy_inclinada | 1 | 0/1 | 13/18 (72%) | 1 |
| pantalla | reflejo | 1 | 1/1 | 18/18 (100%) | 0 |
| papel | borrosa | 1 | 0/1 | 7/8 (88%) | 0 |
| papel | frente | 10 | 10/10 | 78/79 (99%) | 0 |
| papel | inclinada | 3 | 3/3 | 21/23 (91%) | 0 |
| papel | luz_tenue | 2 | 2/2 | 10/10 (100%) | 0 |
| papel | muy_inclinada | 1 | 1/1 | 4/4 (100%) | 0 |
| papel | sombra | 2 | 0/2 | 13/18 (72%) | 2 |

## 3. Tiempo del solver por tamaño de tablero

Solo las imágenes donde se llamó a CP-SAT. Ramas y conflictos son los que reporta CP-SAT (sumados si hubo reintento).

| n | Imágenes | Tiempo mín | Tiempo prom | Tiempo máx | Ramas máx | Conflictos máx |
|---|---|---|---|---|---|---|
| 3×3 | 14 | 0.3 ms | 4.0 ms | 9.5 ms | 115 | 0 |
| 4×4 | 11 | 8.9 ms | 12.3 ms | 19.9 ms | 215 | 11 |
| 5×5 | 16 | 3.9 ms | 12.8 ms | 20.2 ms | 1073 | 24 |
| 6×6 | 2 | 12.6 ms | 17.1 ms | 21.6 ms | 294 | 0 |
| 7×7 | 13 | 15.3 ms | 27.3 ms | 59.9 ms | 1620 | 44 |

## 4. Fotos que no se resuelven bien

| Imagen | Estado | Reintento | OCR | Celdas blancas | Causa |
|---|---|---|---|---|---|
| `KC_kakuro_07x07_dificil_pantalla_muy_inclinada.jpg` | `PISTAS_FUERA_DE_RANGO` | sí | 13/18 | no | 5 celdas blancas del extremo lejano salen como oscuras; los grupos quedan sin sumas posibles. |
| `L_kakuro_03x03_clasico_06_papel_sombra.jpg` | `INFEASIBLE` | sí | 3/4 | sí | La sombra tapa el "1" de 15 y se lee 5. El solver demuestra que no hay solución: rechazo correcto, no inventa la pista. |
| `L_kakuro_05x05_clasico_01_papel_borrosa.jpg` | `OPTIMAL` | no | 7/8 | sí | 309×307 px (~60 px por celda). Lee 16 en vez de 18, ajusta 3→5 y encuentra **otro Kakuro válido**: error silencioso. |
| `L_kakuro_07x07_clasico_01_papel_sombra.jpg` | `PISTAS_SIN_LECTURA` | sí | 10/14 | no | La sombra mueve el umbral y 9 celdas oscuras pasan como blancas; aparece una "pista" sin número. |

## 5. Pistas ajustadas por el solver

Una pista ajustada es una suma que el solver cambió respecto del primer candidato del OCR, usando la tabla de confusiones de dígitos.

| Imagen | Ajustes | ¿Solución correcta? |
|---|---|---|
| `KC_kakuro_05x05_facil_pantalla_moire.png` | 3,1 derecha: 13->18 | sí |
| `KC_kakuro_07x07_intermedio_pantalla_inclinada.jpg` | 5,4 abajo: 42->12 | sí |
| `L_kakuro_05x05_clasico_01_papel_borrosa.jpg` | 2,3 derecha: 3->5 | **no** |
| `L_kakuro_06x06_clasico_01_papel_frente.jpg` | 2,4 derecha: 41->11 | sí |
| `L_kakuro_07x07_clasico_02_papel_inclinada.jpg` | 2,3 abajo: 42->12; 3,4 abajo: 45->15 | sí |

4 de los 6 ajustes son un "1" junto a la diagonal leído como "4" (42→12, 41→11, 45→15). Se podría probar un `DESPLAZAMIENTO_DIAGONAL` mayor que 0.09 en `config.py` y medir de nuevo.

## 6. Historial

| Métrica | Notebook viejo (31 digitales) | Grupo3, JSON sin corregir (31 digitales) | Actual (31 digitales) |
|---|---|---|---|
| Tamaño de grilla correcto | 17/31 | 29/31 | 31/31 |
| Celdas blancas correctas | 17/17 | 29/31 | 31/31 |
| OCR, primer candidato | 70/119 (59%) | 251/261 (96%) | 261/261 (100%) |
| Solución correcta | 6/31 | 29/31 | 31/31 |
| Incorrectas presentadas como correctas | 8 | 2 | 0 |

Entre "Grupo3" y "Actual" no cambió el código: la diferencia son los 2 JSON corregidos (`gris_08`, `gris_06`). `src/kakuro/` reproduce el notebook Grupo3 sin diferencias en 59 imágenes. El OCR del notebook viejo usa otro denominador: solo contaba las 17 imágenes con grilla correcta.
