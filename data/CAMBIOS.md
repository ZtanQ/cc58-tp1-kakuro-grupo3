# Registro de cambios al dataset

Los PNG originales no se modifican. Aquí se registra toda corrección a los
JSON, renombre o movimiento de archivos.

## 2026-09-30 — Bloque 1: JSON de las imágenes "gris" que no correspondían

Los JSON describían un tablero más grande que la imagen, con una fila y una
columna sin celdas blancas ni pistas. Se quitaron y se reindexó todo
(`n`, `celdas_blancas`, `pistas[].origen` y las claves de `solucion`).
Los valores de las pistas y de la solución no cambian.

| JSON | Antes | Fila quitada | Columna quitada | Después |
|---|---|---|---|---|
| `L_kakuro_03x03_gris_08.json` | n=4 | 4 (última) | 1 | n=3 |
| `L_kakuro_04x04_gris_06.json` | n=5 | 1 | 1 | n=4 |

Nota: en `gris_08` la fila vacía era la **última**, no la primera.

Verificado después del cambio: las sumas cuadran, no hay dígitos repetidos
por grupo, cada celda blanca está en exactamente un grupo horizontal y uno
vertical, la solución es única (CP-SAT no encuentra otra) y las pistas
coinciden con lo que se ve en la imagen.

## 2026-09-30 — Bloque 2: campo "imagen" y carpeta soluciones/

### Campo `"imagen"` alineado con el nombre real del archivo

Se cambió solo el valor de `"imagen"` (reemplazo de texto; el resto del
archivo queda byte a byte igual). El valor viejo conserva la nomenclatura
con la que se generó cada puzzle (`L1_`, `L2_`...), por eso se registra aquí.

| JSON | `"imagen"` antes | `"imagen"` después |
|---|---|---|
| `L_kakuro_03x03_clasico_01.json` | `L1_kakuro_03x03_clasico_01.png` | `L_kakuro_03x03_clasico_01.png` |
| `L_kakuro_03x03_clasico_02.json` | `L1_kakuro_03x03_clasico_05.png` | `L_kakuro_03x03_clasico_02.png` |
| `L_kakuro_03x03_clasico_03.json` | `L2_kakuro_03x03_clasico_01.png` | `L_kakuro_03x03_clasico_03.png` |
| `L_kakuro_03x03_clasico_04.json` | `L3_kakuro_03x03_clasico_05.png` | `L_kakuro_03x03_clasico_04.png` |
| `L_kakuro_03x03_clasico_05.json` | `L4_kakuro_03x03_clasico_01.png` | `L_kakuro_03x03_clasico_05.png` |
| `L_kakuro_03x03_clasico_06.json` | `L4_kakuro_03x03_clasico_03.png` | `L_kakuro_03x03_clasico_06.png` |
| `L_kakuro_03x03_gris_08.json` | `kakuro_04x04_gris_05.png` | `L_kakuro_03x03_gris_08.png` |
| `L_kakuro_04x04_clasico_01.json` | `L1_kakuro_04x04_clasico_02.png` | `L_kakuro_04x04_clasico_01.png` |
| `L_kakuro_04x04_clasico_02.json` | `L2_kakuro_04x04_clasico_05.png` | `L_kakuro_04x04_clasico_02.png` |
| `L_kakuro_04x04_clasico_03.json` | `L4_kakuro_04x04_clasico_02.png` | `L_kakuro_04x04_clasico_03.png` |
| `L_kakuro_04x04_gris_06.json` | `kakuro_05x05_gris_06.png` | `L_kakuro_04x04_gris_06.png` |
| `L_kakuro_05x05_clasico_01.json` | `L2_kakuro_05x05_clasico_03.png` | `L_kakuro_05x05_clasico_01.png` |
| `L_kakuro_05x05_clasico_02.json` | `L1_kakuro_05x05_clasico_06.png` | `L_kakuro_05x05_clasico_02.png` |
| `L_kakuro_05x05_clasico_03.json` | `L4_kakuro_05x05_clasico_05.png` | `L_kakuro_05x05_clasico_03.png` |
| `L_kakuro_05x05_gris_01.json` | `L4_kakuro_05x05_gris_02.png` | `L_kakuro_05x05_gris_01.png` |
| `L_kakuro_05x05_gris_02.json` | `kakuro_05x05_gris_02.png` | `L_kakuro_05x05_gris_02.png` |
| `L_kakuro_06x06_clasico_01.json` | `L1_kakuro_06x06_clasico_07.png` | `L_kakuro_06x06_clasico_01.png` |
| `L_kakuro_07x07_clasico_01.json` | `L1_kakuro_07x07_clasico_04.png` | `L_kakuro_07x07_clasico_01.png` |
| `L_kakuro_07x07_clasico_02.json` | `L2_kakuro_07x07_clasico_08.png` | `L_kakuro_07x07_clasico_02.png` |
| `L_kakuro_07x07_gris_03.json` | `kakuro_07x07_gris_08.png` | `L_kakuro_07x07_gris_03.png` |

### `data/soluciones/` renombrada a `{base}_solucion.png`

Los nombres usaban la nomenclatura vieja y no coincidían con `original/`.
Cada imagen se emparejó con su JSON comparando todas las pistas y todos los
dígitos de la solución dibujada (las 11 coinciden con un único JSON).
Solo 11 de las 31 imágenes tienen solución de referencia.

| Antes | Después |
|---|---|
| `kakuro_03x03_clasico_01_solucion.png` | `L_kakuro_03x03_clasico_05_solucion.png` |
| `kakuro_03x03_clasico_03_solucion.png` | `L_kakuro_03x03_clasico_06_solucion.png` |
| `kakuro_04x04_clasico_02_solucion.png` | `L_kakuro_04x04_clasico_03_solucion.png` |
| `kakuro_05x05_clasico_05_solucion.png` | `L_kakuro_05x05_clasico_03_solucion.png` |
| `L2_kakuro_04x04_clasico_01_solucion.png` | `L_kakuro_03x03_clasico_03_solucion.png` |
| `L2_kakuro_04x04_clasico_05_solucion.png` | `L_kakuro_04x04_clasico_02_solucion.png` |
| `L2_kakuro_06x06_clasico_03_solucion.png` | `L_kakuro_05x05_clasico_01_solucion.png` |
| `L2_kakuro_07x07_clasico_08_solucion.png` | `L_kakuro_07x07_clasico_02_solucion.png` |
| `L5_kakuro_04x04_clasico_01_solucion.png` | `L_kakuro_04x04_clasico_04_solucion.png` |
| `L5_kakuro_04x04_clasico_05_solucion.png` | `L_kakuro_03x03_clasico_07_solucion.png` |
| `L5_kakuro_05x05_clasico_06_solucion.png` | `L_kakuro_04x04_clasico_05_solucion.png` |

## 2026-09-30 — Bloque 3: fotos integradas al dataset y caso de rechazo

### Fotos de `data/variaciones/` → `data/original/`

Las 27 son fotos reales con celular (26 con EXIF de Samsung SM-A226BR; la
de moiré es una captura recortada y exportada a PNG sin EXIF). Los archivos
se movieron sin modificarlos (`git mv`).

Esquema de nombre: `{base}_{soporte}_{condicion}.{ext}`
- `base`: nombre de la imagen digital de `original/` que se fotografió.
- `soporte`: `papel` (impresa, 19 fotos) o `pantalla` (monitor, 8 fotos).
- `condicion`: `frente`, `inclinada`, `muy_inclinada`, `luz_tenue`,
  `sombra`, `reflejo`, `borrosa`, `moire` (solo ASCII; se unificó
  `luztenue`/`poca_luz` → `luz_tenue`, `angulo` → `inclinada`,
  `con_sombra` → `sombra`, `moiré` → `moire`).

Cada foto tiene un JSON mínimo en `ground_truth/` con `"imagen"`, `"base"` y
`"fuente"`. Las celdas, pistas y solución se leen del JSON de la base, así
que una corrección a la base vale también para sus fotos.

| Antes | Después | Base |
|---|---|---|
| `variaciones/KC_kakuro_05x05_experto_poca_luz.jpg` | `original/KC_kakuro_05x05_experto_pantalla_luz_tenue.jpg` | `KC_kakuro_05x05_experto` |
| `variaciones/KC_kakuro_05x05_facil_angulo.jpg` | `original/KC_kakuro_05x05_facil_pantalla_inclinada.jpg` | `KC_kakuro_05x05_facil` |
| `variaciones/KC_kakuro_05x05_facil_frente.jpg` | `original/KC_kakuro_05x05_facil_pantalla_frente.jpg` | `KC_kakuro_05x05_facil` |
| `variaciones/KC_kakuro_05x05_facil_moiré.png` | `original/KC_kakuro_05x05_facil_pantalla_moire.png` | `KC_kakuro_05x05_facil` |
| `variaciones/KC_kakuro_07x07_dificil_muy_inclinado.jpg` | `original/KC_kakuro_07x07_dificil_pantalla_muy_inclinada.jpg` | `KC_kakuro_07x07_dificil` |
| `variaciones/KC_kakuro_07x07_dificil_reflejo.jpg` | `original/KC_kakuro_07x07_dificil_pantalla_reflejo.jpg` | `KC_kakuro_07x07_dificil` |
| `variaciones/KC_kakuro_07x07_intermedio_frente.jpg` | `original/KC_kakuro_07x07_intermedio_pantalla_frente.jpg` | `KC_kakuro_07x07_intermedio` |
| `variaciones/KC_kakuro_07x07_intermedio_inclinado.jpg` | `original/KC_kakuro_07x07_intermedio_pantalla_inclinada.jpg` | `KC_kakuro_07x07_intermedio` |
| `variaciones/L_kakuro_03x03_clasico_01_impresa_frente.jpg` | `original/L_kakuro_03x03_clasico_01_papel_frente.jpg` | `L_kakuro_03x03_clasico_01` |
| `variaciones/L_kakuro_03x03_clasico_01_impresa_luztenue.jpg` | `original/L_kakuro_03x03_clasico_01_papel_luz_tenue.jpg` | `L_kakuro_03x03_clasico_01` |
| `variaciones/L_kakuro_03x03_clasico_06_impresa_con_sombra.jpg` | `original/L_kakuro_03x03_clasico_06_papel_sombra.jpg` | `L_kakuro_03x03_clasico_06` |
| `variaciones/L_kakuro_03x03_clasico_06_impresa_frente.jpg` | `original/L_kakuro_03x03_clasico_06_papel_frente.jpg` | `L_kakuro_03x03_clasico_06` |
| `variaciones/L_kakuro_03x03_clasico_06_impresa_inclinada.jpg` | `original/L_kakuro_03x03_clasico_06_papel_inclinada.jpg` | `L_kakuro_03x03_clasico_06` |
| `variaciones/L_kakuro_03x03_clasico_06_impresa_muy_inclinada.jpg` | `original/L_kakuro_03x03_clasico_06_papel_muy_inclinada.jpg` | `L_kakuro_03x03_clasico_06` |
| `variaciones/L_kakuro_04x04_clasico_02_impresa_frente.jpg` | `original/L_kakuro_04x04_clasico_02_papel_frente.jpg` | `L_kakuro_04x04_clasico_02` |
| `variaciones/L_kakuro_04x04_clasico_02_impresa_inclinada.jpg` | `original/L_kakuro_04x04_clasico_02_papel_inclinada.jpg` | `L_kakuro_04x04_clasico_02` |
| `variaciones/L_kakuro_04x04_clasico_03_impresa_frente.jpg` | `original/L_kakuro_04x04_clasico_03_papel_frente.jpg` | `L_kakuro_04x04_clasico_03` |
| `variaciones/L_kakuro_04x04_clasico_03_impresa_luztenue.jpg` | `original/L_kakuro_04x04_clasico_03_papel_luz_tenue.jpg` | `L_kakuro_04x04_clasico_03` |
| `variaciones/L_kakuro_04x04_gris_06_impresa_frente.jpg` | `original/L_kakuro_04x04_gris_06_papel_frente.jpg` | `L_kakuro_04x04_gris_06` |
| `variaciones/L_kakuro_05x05_clasico_01_impresa_borrosa.jpg` | `original/L_kakuro_05x05_clasico_01_papel_borrosa.jpg` | `L_kakuro_05x05_clasico_01` |
| `variaciones/L_kakuro_05x05_clasico_01_impresa_frente.jpg` | `original/L_kakuro_05x05_clasico_01_papel_frente.jpg` | `L_kakuro_05x05_clasico_01` |
| `variaciones/L_kakuro_05x05_gris_01_impresa_frente.jpg` | `original/L_kakuro_05x05_gris_01_papel_frente.jpg` | `L_kakuro_05x05_gris_01` |
| `variaciones/L_kakuro_06x06_clasico_01_impresa_frente.jpg` | `original/L_kakuro_06x06_clasico_01_papel_frente.jpg` | `L_kakuro_06x06_clasico_01` |
| `variaciones/L_kakuro_07x07_clasico_01_impresa_con_sombra.jpg` | `original/L_kakuro_07x07_clasico_01_papel_sombra.jpg` | `L_kakuro_07x07_clasico_01` |
| `variaciones/L_kakuro_07x07_clasico_01_impresa_frente.jpg` | `original/L_kakuro_07x07_clasico_01_papel_frente.jpg` | `L_kakuro_07x07_clasico_01` |
| `variaciones/L_kakuro_07x07_clasico_02_impresa_frente.jpg` | `original/L_kakuro_07x07_clasico_02_papel_frente.jpg` | `L_kakuro_07x07_clasico_02` |
| `variaciones/L_kakuro_07x07_clasico_02_impresa_inclinada.jpg` | `original/L_kakuro_07x07_clasico_02_papel_inclinada.jpg` | `L_kakuro_07x07_clasico_02` |

La carpeta `data/variaciones/` quedó vacía y se eliminó.

### Foto con oclusión → `data/rechazo/`

| Antes | Después |
|---|---|
| `L_kakuro_06x06_clasico_07_impresa_con_perro.jpg.jpeg` (raíz del repo) | `data/rechazo/L_kakuro_07x07_clasico_01_papel_oclusion.jpeg` |

El nombre viejo era incorrecto: es la versión impresa de
`L_kakuro_07x07_clasico_01` (7×7), no un 6×6. El perro tapa la esquina
superior izquierda y varias pistas, así que el comportamiento correcto es
rechazarla. No lleva JSON: `evaluar.py` la cuenta como acierto si el sistema
no presenta solución.
