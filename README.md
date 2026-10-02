# Kakuro Solver

Trabajo 1 de CC58 — Tópicos en Ciencia de la Computación (UPC).

Recibe la foto o captura de un **Kakuro** y devuelve el puzzle resuelto, dibujado sobre la imagen:

1. **Visión computacional (OpenCV):** encuentra el tablero, corrige la perspectiva, detecta el tamaño de la grilla (3×3 a 7×7, contando las celdas de pistas) y separa las celdas blancas de las celdas de pista.
2. **OCR (Tesseract):** lee las sumas de cada celda de pista.
3. **Constraint Programming (OR-Tools CP-SAT):** resuelve el puzzle. Las sumas leídas son "variables de percepción": si una lectura no forma un Kakuro válido, el solver puede usar una cifra parecida (por ejemplo 3 → 8), pagando un costo, y elige la combinación de menor costo.
4. **Visualización:** escribe la solución sobre la imagen rectificada.

Si una pista no se pudo leer, el sistema **no inventa** la suma: responde `PISTAS_SIN_LECTURA` y no presenta solución.

---

## Resultados

Medidos con `scripts/evaluar.py` (Tesseract 5.3.4) sobre las 58 imágenes de `data/original/`, comparando cada una con su JSON de `data/ground_truth/`.

| Métrica | Digital | Foto papel | Foto pantalla | **Total** |
|---|---|---|---|---|
| Imágenes | 31 | 19 | 8 | **58** |
| Tamaño de grilla correcto | 31/31 | 19/19 | 8/8 | **58/58** |
| Celdas blancas correctas | 31/31 | 18/19 | 7/8 | **56/58** |
| OCR, pista correcta en primer candidato | 261/261 (100%) | 133/142 (94%) | 93/100 (93%) | **487/503 (97%)** |
| JSON exportado = ground truth | 31/31 | 14/19 | 5/8 | **50/58** |
| **Solución correcta** | **31/31** | **16/19** | **7/8** | **54/58** |
| Incorrectas presentadas como correctas | 0 | 1 | 0 | **1** |
| Sin solución (el sistema no inventa) | 0 | 2 | 1 | **3** |
| Usaron el reintento con filtro de bandas | 0 | 2 | 2 | **4** |
| Pistas ajustadas por el solver | 0 | 4 | 2 | **6** |
| Tiempo del solver | 1–60 ms | 0–23 ms | 8–30 ms | **0–60 ms** |

- La foto con oclusión de `data/rechazo/` se rechaza correctamente (1/1).
- Casi todo el tiempo se va en el OCR, no en el solver. En Colab una imagen digital tarda ~3.4 s; en Docker sobre Windows, entre 5 y 13 s. Las fotos que usan el reintento con filtro de bandas tardan hasta ~40 s.
- El detalle por imagen queda en `resultados/metricas.csv`, las tablas para el informe en [`resultados/resumen.md`](resultados/resumen.md) y el cruce con el enunciado y la rúbrica en [`resultados/auditoria.md`](resultados/auditoria.md).

---

## Instalación

Se necesita **Python 3.10 o superior** y **Tesseract OCR** instalado en el sistema.

### 1. Tesseract

| Sistema | Comando |
|---|---|
| Ubuntu / Debian / Colab | `sudo apt-get install -y tesseract-ocr` |
| macOS | `brew install tesseract` |
| Windows | Instalador de UB Mannheim: https://github.com/UB-Mannheim/tesseract/wiki. Agrega `C:\Program Files\Tesseract-OCR` al `PATH`. |

Comprueba que quedó instalado:

```bash
tesseract --version
```

Los resultados de arriba se midieron con **Tesseract 5.3.4** (el de Ubuntu 24.04). Otra versión puede cambiar un poco la lectura de las pistas.

### 2. Librerías de Python

Desde la carpeta del proyecto:

```bash
pip install -r requirements.txt
```

`requirements.txt` fija las versiones que usa el equipo: `opencv-python-headless==5.0.0.93`, `pytesseract==0.3.13`, `ortools==9.15.6755`, `numpy`, `matplotlib` y `pytest==9.1.1` (solo para las pruebas).

---

## Resolver una imagen

El código está en `src/kakuro/`, así que `src` tiene que estar en el `PYTHONPATH`.

**Linux / macOS:**

```bash
PYTHONPATH=src python -m kakuro.pipeline data/original/L_kakuro_07x07_clasico_01.png --salida resuelto.png --json estado.json
```

**Windows (PowerShell):**

```powershell
$env:PYTHONPATH = "src"
python -m kakuro.pipeline data/original/L_kakuro_07x07_clasico_01.png --salida resuelto.png --json estado.json
```

- `--salida`: imagen con la solución dibujada (por defecto `kakuro_resuelto.png`).
- `--json`: guarda el estado inicial leído (tablero y pistas) con el formato de `data/ground_truth/`.

El programa imprime el estado del modelo, los tiempos y las pistas que el solver ajustó. Devuelve 0 si hubo solución y 1 si no.

### Desde Python

```python
import sys
sys.path.insert(0, "src")

from kakuro.pipeline import resolver_imagen
from kakuro.estructura import exportar_json
from kakuro.visualizacion import dibujar_solucion

resultado = resolver_imagen("data/original/L_kakuro_03x03_clasico_06.png")
print(resultado.estado)        # "OPTIMAL", "PISTAS_SIN_LECTURA", "INFEASIBLE", ...
print(resultado.solucion)      # {(fila, columna): dígito} o None
print(resultado.obtener("ajustes"))
estado = exportar_json(resultado, "estado.json", nombre_imagen="L_kakuro_03x03_clasico_06.png")
imagen = dibujar_solucion(resultado.a_dict())
```

### Demo en Colab

Abre `notebooks/demo_colab.ipynb` en Google Colab y ejecuta las celdas en orden. La primera celda carga el código de una de dos formas:
- clonando el repositorio (`OPCION = "clonar"` y la URL en `REPO_URL`);
- subiendo la carpeta del proyecto comprimida como `kakuro-solver.zip` (`OPCION = "subir"`, la opción por defecto mientras el repositorio no esté publicado).

Después pide una imagen y muestra la original, la solución, las pistas ajustadas, los tiempos y el JSON exportado.

---

## Evaluar el dataset

```bash
python scripts/evaluar.py --datos data --salida resultados/
```

- Recorre `data/original/`, compara cada imagen con su JSON y evalúa aparte `data/rechazo/`, donde el acierto es **no** presentar solución. Con `--rechazo` se pueden indicar otras carpetas o imágenes de rechazo.
- Antes de empezar, valida que todo JSON con `"base"` apunte a una imagen original existente.
- Imprime una tabla por tipo de imagen (digital, foto de papel, foto de pantalla) y en total.
- Guarda:
  - `resultados/metricas.csv`: una fila por imagen (estado, etapa de error, pistas leídas, ajustes, tiempos, etc.);
  - `resultados/rechazo.csv`;
  - `resultados/soluciones/`: imágenes resueltas;
  - `resultados/json/`: estado inicial exportado de cada imagen.

La evaluación completa tarda unos 8 minutos.

Otros dos scripts:

```bash
# Tablas para el informe (resultados/resumen.md) a partir de los CSV de evaluar.py
python scripts/generar_resumen.py --resultados resultados --condiciones "Tesseract 5.3.4, commit abc1234"

# Verifica que cada JSON de data/ground_truth/ sea un Kakuro válido: sumas, sin repetidos,
# cobertura y solución única. En las fotos, que su "base" exista. Termina con código 1 si hay errores.
python scripts/verificar_ground_truth.py --datos data
```

---

## Pruebas

```bash
python -m pytest tests
```

Son 72 pruebas rápidas y deterministas, sin OCR (tardan unos segundos):

- `tests/test_modelo_cp.py`: un Kakuro 3×3 conocido se resuelve con la solución correcta; pistas imposibles dan `INFEASIBLE`; una pista sin lectura da `PISTAS_SIN_LECTURA` sin llamar al solver.
- `tests/test_estructura.py`: `construir_grupos` rechaza un grupo de 1 celda y una cobertura incompleta; `exportar_json` produce el formato del ground truth y marca las pistas sin lectura.
- `tests/test_ground_truth.py`: todos los JSON de `data/ground_truth/` pasan `verificar_ground_truth.py`, y el verificador detecta un tablero roto y uno con dos soluciones.

Las pruebas no reemplazan a `scripts/evaluar.py`, que es la que mide visión y OCR sobre las imágenes.

---

## Estructura

```
├── README.md
├── requirements.txt
├── Kakuro_Solver_Grupo3.ipynb # notebook original del equipo (fuente de la migración)
├── src/kakuro/
│   ├── config.py             # todas las constantes y umbrales, agrupados por etapa
│   ├── tablero.py            # localizar el tablero y corregir la perspectiva
│   ├── cuadricula.py         # detectar n y las líneas de la grilla
│   ├── celdas.py             # recortar celdas y separar blancas de pistas
│   ├── ocr.py                # preparar los números, leerlos con Tesseract, filtro de bandas
│   ├── estructura.py         # grupos de celdas, validación y exportar_json
│   ├── modelo_cp.py          # modelo CP-SAT: dominios, variables, restricciones, objetivo
│   ├── visualizacion.py      # dibujar la solución
│   └── pipeline.py           # procesar_imagen / resolver_imagen y la línea de comandos
├── scripts/
│   ├── evaluar.py            # evaluación contra el ground truth
│   ├── generar_resumen.py    # resultados/resumen.md desde los CSV
│   └── verificar_ground_truth.py  # sumas, cobertura y unicidad de los JSON
├── tests/                    # pytest: modelo CP, estructura y ground truth (sin OCR)
├── notebooks/demo_colab.ipynb
├── data/
│   ├── original/             # 58 imágenes: 31 digitales + 19 fotos de papel + 8 de pantalla
│   ├── ground_truth/         # un JSON por imagen, con el mismo nombre base
│   ├── rechazo/              # imágenes que el sistema debe rechazar
│   ├── soluciones/           # soluciones de referencia de algunos puzzles
│   └── CAMBIOS.md            # registro de toda corrección al dataset
└── resultados/               # salida de evaluar.py; en git solo están resumen.md y auditoria.md
```

**Nombres de las fotos:** `{base}_{soporte}_{condicion}.{ext}` (casi todas `.jpg`; la de moiré es `.png`), donde `base` es la imagen digital fotografiada, `soporte` es `papel` o `pantalla`, y `condicion` es una de `frente`, `inclinada`, `muy_inclinada`, `luz_tenue`, `sombra`, `reflejo`, `borrosa` o `moire`.

---

## Formato de los JSON

Coordenadas `(fila, columna)` empezando en 1. La fila 1 y la columna 1 siempre son pistas o celdas vacías.

**Imagen digital** (`data/ground_truth/<nombre>.json`):

```json
{
  "imagen": "L_kakuro_03x03_clasico_07.png",
  "n": 3,
  "celdas_blancas": [[2, 2], [2, 3], [3, 2], [3, 3]],
  "pistas": [
    {"origen": [1, 2], "derecha": null, "abajo": 12},
    {"origen": [2, 1], "derecha": 15, "abajo": null}
  ],
  "solucion": {"2,2": 9, "2,3": 6, "3,2": 3, "3,3": 1}
}
```

- `derecha`: suma de las celdas blancas que empiezan a la derecha de la pista.
- `abajo`: suma de las que empiezan debajo.
- `null`: no hay suma en esa dirección.

**Foto:** no repite el tablero, apunta a su imagen digital con `"base"`:

```json
{
  "imagen": "L_kakuro_03x03_clasico_06_papel_sombra.jpg",
  "base": "L_kakuro_03x03_clasico_06",
  "fuente": "foto con celular (Samsung SM-A226BR) de L_kakuro_03x03_clasico_06 impreso en papel; condición: sombra"
}
```

**Estado inicial exportado** (`--json` o `exportar_json`): mismo formato que el de una imagen digital, sin `solucion`, con el primer candidato del OCR en cada pista y una lista extra `pistas_sin_lectura` (`[fila, columna, direccion]`). Esa lista distingue una pista que no se leyó de una dirección sin pista.

---

## Limitaciones conocidas

- **Sombras fuertes o inclinación extrema:** pueden hacer que algunas celdas se clasifiquen mal. En esos casos el sistema responde sin solución en vez de inventarla.
- **Imágenes de muy baja resolución:** con ~60 px por celda, una lectura equivocada puede formar otro Kakuro válido, y el sistema lo presenta como solución (`L_kakuro_05x05_clasico_01_papel_borrosa`).
- **Oclusión:** si un objeto tapa el borde del tablero, se rechaza la imagen en la etapa "tablero".

## Referencias

- M. Mulamba et al., *Perception-based constraint solving for sudoku images*, Constraints 29 (2024). Base de la idea de las "variables de percepción".
- Tesseract OCR: https://github.com/tesseract-ocr/tesseract
- OR-Tools CP-SAT: https://developers.google.com/optimization/cp/cp_solver
- Los puzzles `KC_*` son de Kakuro Conquest (https://www.kakuroconquest.com), usados con permiso de Hey, Good Game, exclusivamente con fines académicos y no comerciales. Los puzzles pertenecen a sus autores y no se presentan como propios.

