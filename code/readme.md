# Generador de Kakuros (`generar_kakuro.py`)

Script que genera puzzles de Kakuro con **solución única**, junto con su imagen y su *ground truth* en JSON. Se usó para completar el dataset de prueba del pipeline de visión por computadora.

## Resumen

- Construye cada puzzle **a partir de una solución** y calcula las pistas sumando, así que siempre tiene solución.
- Verifica con OR-Tools (CP-SAT) que esa solución sea la **única**.
- Dibuja la imagen del tablero vacío (PNG) y guarda la respuesta correcta en un JSON.
- Opcionalmente genera un PDF para imprimir y la imagen con la solución escrita.
- No usa código del pipeline ni copia puzzles de ninguna web.

## Requisitos

- Python 3
- `ortools` y `pillow`

```bash
pip install ortools pillow
```

## Uso rápido

```bash
# 8 puzzles de tamaños 4, 5, 6 y 7, con PDF para imprimir
python code\generar_kakuro.py --cantidad 8 --pdf

# Un lote distinto, con otra semilla y otra carpeta de salida
python code\generar_kakuro.py --cantidad 5 --tamanos 3 4 6 --semilla 500 --salida data\generado2

# Estilo gris (celdas de pista grises con números negros)
python code\generar_kakuro.py --cantidad 2 --tamanos 4 6 --estilo gris --semilla 300 --salida data\lote_gris
```

## Opciones

| Opción | Valor por defecto | Descripción |
|---|---|---|
| `--cantidad` | `8` | Cuántos puzzles generar. |
| `--tamanos` | `4 5 6 7` | Tamaños `n` permitidos (de 3 a 7). Se reparten en orden cíclico. |
| `--salida` | `data\generado` | Carpeta de salida. |
| `--semilla` | `42` | Semilla aleatoria. Misma semilla y misma versión del script, mismos puzzles. |
| `--estilo` | `clasico` | `clasico` (negro con números blancos) o `gris` (gris con números negros). |
| `--sin-separadores` | desactivado | Quita las líneas claras entre celdas negras vecinas. |
| `--pdf` | desactivado | Crea `kakuros_para_imprimir.pdf` (una hoja A4 por puzzle). |
| `--con-solucion` | desactivado | Guarda también cada puzzle con la solución escrita. |

## Salidas

```
<salida>/
├── imagenes/        kakuro_05x05_clasico_02.png
├── ground_truth/    kakuro_05x05_clasico_02.json
├── soluciones/      (solo con --con-solucion)
├── metadata.csv
└── kakuros_para_imprimir.pdf   (solo con --pdf)
```

Los archivos se nombran `kakuro_{n}x{n}_{estilo}_{número}`. **Ojo:** el número es solo el orden dentro del lote. Dos lotes guardados en la misma carpeta se sobrescriben entre sí.

`metadata.csv` tiene las columnas `archivo, n, estilo, tipo, condicion, detalle, origen`. El script solo escribe imágenes digitales limpias, así que `tipo` es siempre `digital`.

## Convenciones

- **Tamaño `n`:** cuenta el tablero **completo**, incluyendo la fila y la columna de pistas. Un `5x5` tiene como máximo 4×4 casillas para rellenar.
- **Coordenadas:** `(fila, columna)` empezando desde 1.
- **Pistas:** el número de arriba a la derecha de una celda es la suma de la fila hacia la derecha (`derecha`). El de abajo a la izquierda es la suma de la columna hacia abajo (`abajo`).

## Formato del JSON

```json
{
  "imagen": "kakuro_03x03_clasico_01.png",
  "n": 3,
  "estilo": "clasico",
  "celdas_blancas": [[2, 2], [2, 3], [3, 2], [3, 3]],
  "pistas": [
    {"origen": [1, 2], "derecha": null, "abajo": 12},
    {"origen": [1, 3], "derecha": null, "abajo": 7},
    {"origen": [2, 1], "derecha": 15, "abajo": null},
    {"origen": [3, 1], "derecha": 4, "abajo": null}
  ],
  "solucion": {"2,2": 9, "2,3": 6, "3,2": 3, "3,3": 1}
}
```

`origen` es la celda de pista que controla cada suma. `null` significa que esa celda no tiene pista en esa dirección.

## Cómo funciona

1. **Forma.** La primera fila y la primera columna son celdas de pista. El resto se rellena al azar con casillas blancas o negras, y se quitan las casillas que queden aisladas, porque en Kakuro toda secuencia de casillas blancas debe tener al menos 2.
2. **Solución.** Se llenan las casillas con dígitos del 1 al 9, sin repetir dentro de ninguna fila ni columna (búsqueda con retroceso y orden aleatorio).
3. **Pistas.** Cada pista es la suma de los dígitos de su secuencia.
4. **Unicidad.** Con CP-SAT se busca una solución distinta de la original. Si no existe, el puzzle es único.
5. **Reparación.** Si existe otra solución, se prueban otras soluciones para la misma forma. Si ninguna sirve, se pone en negro una casilla donde las dos soluciones difieren y se repite el proceso.
6. **Imagen y JSON.** Se dibuja con Pillow y se guarda el ground truth.

Los tableros de 7×7 pueden tardar hasta un minuto. Si un puzzle no se logra después de varios reintentos, el script lo omite con un aviso.

## Reproducibilidad y duplicados

- La semilla por defecto es la misma siempre. **Usa una semilla distinta en cada lote** o repetirás puzzles, y una carpeta de salida distinta para no sobrescribir archivos.
- Los resultados dependen de la versión del script. Versiones distintas generan puzzles distintos con la misma semilla, así que conviene guardar el script junto con el dataset.
- El script no detecta duplicados entre ejecuciones. Los tableros pequeños tienden a repetir el mismo diseño (un bloque de 2×2) con números distintos.

## Limitaciones conocidas

- **Bordes vacíos.** El generador no obliga a usar todo el tablero. Algunos puzzles quedan con filas o columnas negras vacías en el borde, y su tamaño real es menor que el de la etiqueta. En estos casos a mano se tuvo que separar las que servían de las que directamente no.
- **Un solo estilo visual.** Las imágenes son digitales, nítidas y muy regulares, sin ruido ni deformaciones. Las fotos (impresas o de pantalla) se tomaron aparte.
- **Rango de tamaños.** El script acepta de 3 a 7, que es el rango que admite el pipeline. No es un límite del Kakuro.
- **Límite de tiempo.** La comprobación de unicidad tiene un máximo de 10 segundos por puzzle. En los tamaños soportados no esperamos alcanzarlo, pero no lo medimos formalmente.

## Relación con el pipeline

El generador se desarrolló de forma independiente del pipeline de lectura de imágenes: no reutiliza su código ni necesita conocer su implementación para generar los puzzles, comprobar su unicidad o producir el ground truth.

El generador parte de una solución, construye las pistas a partir de ella y utiliza OR-Tools para verificar que esa solución sea única. Esta lógica de generación y validación es independiente de la lógica utilizada posteriormente para detectar y leer los tableros en las imágenes.

Una vez definido el generador, se adoptaron algunas convenciones compatibles con el pipeline y con el formato del dataset. En concreto:

se utiliza el rango de tamaños de 3 a 7, que es el admitido por el pipeline;

se utiliza la posición estándar de los números de las pistas dentro de cada celda, que coincide con las regiones que busca el código de lectura;

se incorporaron líneas grises entre celdas negras vecinas, porque las pruebas con el pipeline mostraron que facilitaban la detección de la cuadrícula. Estas líneas pueden desactivarse con --sin-separadores.

Estas decisiones afectan únicamente a la representación de los puzzles generados, no a la lógica con la que se generan sus soluciones ni a la comprobación de unicidad.

Para reducir el sesgo, el dataset combina estos puzzles con otros de una fuente independiente (ver [atribuciones](../data/ATRIBUCIONES.md)) y con fotos reales.

## Uso en este proyecto

Los puzzles generados se complementaron con capturas y fotos de pantalla de Kakuro Conquest. Sobre los generados se hizo un postproceso manual:

- Se **recortaron las filas y columnas negras vacías** de los bordes para que la etiqueta coincida con el tamaño real. Al recortar, el JSON se ajustó (`n` y coordenadas).
- Se renombraron con un prefijo de lote para evitar nombres repetidos.
- Se imprimieron y fotografiaron en distintas condiciones de luz y ángulo.

El PDF de `--pdf` contiene los tableros sin recortar. Si recortas las imágenes, crear un archivo docs y pasalo a pdf a partir de eso imprime desde las recortadas.

Los JSON del dataset pueden validarse con `scripts/verificar_ground_truth.py`, que comprueba sumas, cobertura y unicidad de la solución.

## Atribución

Este script no usa puzzles de terceros. Las imágenes de Kakuro Conquest que forman parte del dataset están descritas en [data/ATRIBUCIONES.md](../data/ATRIBUCIONES.md).