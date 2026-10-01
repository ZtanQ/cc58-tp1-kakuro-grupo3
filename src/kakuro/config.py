"""Constantes y umbrales del pipeline, agrupados por etapa.

Todos los valores vienen tal cual de Kakuro_Solver_Grupo3.ipynb. Cambiar
cualquiera cambia los resultados: primero se mide con scripts/evaluar.py.

Las fracciones "de la celda" o "de la imagen" son relativas al alto (h) o
ancho (w) de la región que se está procesando.
"""

# =============================================================================
# --- Tablero --- (tablero.py: localizar el tablero y corregir perspectiva)
# =============================================================================

# Lado en píxeles de la imagen cuadrada que sale de la corrección de
# perspectiva. Todo lo demás (cuadrícula, celdas, OCR) trabaja sobre ella.
LADO = 840

# La búsqueda de contornos se hace en una copia cuyo lado mayor mide como
# mucho esto, para que sea rápida. La perspectiva se aplica sobre el original.
ESCALA_MAX = 1100

# Desenfoque antes de buscar bordes del tablero.
KERNEL_DESENFOQUE_TABLERO = (5, 5)

# CLAHE: realza el contraste local para fotos con poca luz o sombras.
CLAHE_LIMITE = 2
CLAHE_CUADRICULA = (8, 8)

# Se buscan contornos en 3 "mapas" distintos de la misma imagen:
# Canny sobre el gris, Canny sobre el gris realzado y umbral adaptativo.
CANNY_TABLERO_GRIS = (25, 85)
CANNY_TABLERO_REALZADA = (35, 100)
BLOQUE_ADAPTATIVO_TABLERO = 51
CONSTANTE_ADAPTATIVA_TABLERO = 8

# Cierre morfológico para unir bordes cortados antes de buscar contornos.
KERNEL_CIERRE_TABLERO = (3, 3)

# Un contorno es candidato a tablero si su área está entre estas fracciones
# del área de la imagen: descarta celdas sueltas y el marco de la foto.
AREA_MIN_TABLERO = 0.06
AREA_MAX_TABLERO = 0.99

# Tolerancias de approxPolyDP (fracción del perímetro). Se prueban de menor a
# mayor y se usa la primera que da un cuadrilátero convexo.
EPSILONS_APROXIMACION = (0.015, 0.025, 0.04)

# Se descarta un cuadrilátero si su lado más corto mide menos que esta
# fracción del más largo (demasiado alargado para ser el tablero).
PROPORCION_LADOS_MIN = 0.25

# Dos cuadriláteros cuyas esquinas difieren en promedio menos de estos
# píxeles se consideran el mismo.
DISTANCIA_CUADRILATERO_REPETIDO = 6

# Cuántos cuadriláteros (los de mayor área) se prueban con detectar_cuadricula.
MAX_CUADRILATEROS = 24

# En el respaldo con Hough, entre los candidatos con puntaje de al menos esta
# fracción del mejor, se elige el de mayor área (el tablero completo y no
# solo una parte).
FRACCION_PUNTAJE_RESPALDO = 0.8

# --- Respaldo con líneas de Hough (si ningún contorno sirvió) ---

# Dos niveles de suavizado (sigma del gaussiano): uno fino y uno grueso.
SIGMAS_HOUGH = (2, 5)

# Canny muy permisivo: en el respaldo interesa no perder ningún borde largo.
CANNY_HOUGH = (4, 16)

# HoughLinesP: resolución de distancia (px), divisor de pi para la resolución
# angular (pi/720 = 0.25°), votos mínimos, largo mínimo como fracción del lado
# menor de la imagen y hueco máximo (px) dentro de una línea.
HOUGH_RESOLUCION_RHO = 1
HOUGH_DIVISOR_ANGULO = 720
HOUGH_UMBRAL = 45
HOUGH_LARGO_MIN = 0.25
HOUGH_HUECO_MAX = 30

# Un segmento es horizontal si |dy| < 0.45·|dx|, vertical si |dx| < 0.45·|dy|.
# Los que quedan en medio (diagonales) se ignoran.
PENDIENTE_MAX_FAMILIA = 0.45

# Dos líneas son la misma si sus centros están a menos de 12 px y sus
# normales difieren menos de 0.08.
DISTANCIA_CENTRO_REPETIDA = 12
DIFERENCIA_NORMAL_REPETIDA = 0.08

# Máximo de líneas (las más largas) que se guardan por familia.
MAX_LINEAS_FAMILIA = 30

# Dos líneas paralelas forman un lado opuesto del tablero solo si están
# separadas más de esta fracción del alto (horizontales) o ancho (verticales).
SEPARACION_MIN_PAREJA = 0.45

# Área válida de un cuadrilátero armado con líneas, como fracción de la imagen.
AREA_MIN_HOUGH = 0.15
AREA_MAX_HOUGH = 0.95

# Máximo de cuadriláteros (los de mayor área) que devuelve el respaldo.
MAX_CANDIDATOS_HOUGH = 250

# Si el producto cruz de dos líneas tiene tercera coordenada menor que esto,
# son paralelas y no se cortan; se devuelve un punto muy lejos para que el
# cuadrilátero se descarte.
TOLERANCIA_PARALELAS = 1e-6
PUNTO_SIN_INTERSECCION = (-1e6, -1e6)

# =============================================================================
# --- Cuadrícula --- (cuadricula.py: detectar n y las líneas)
# =============================================================================

# Tamaños de tablero que se prueban, contando las celdas de pistas.
MIN_N = 3
MAX_N = 7

# Preprocesado para encontrar las líneas de la grilla.
KERNEL_DESENFOQUE_CUADRICULA = (3, 3)
CANNY_CUADRICULA = (20, 80)
KERNEL_DILATACION_CUADRICULA = (3, 3)

# Largo del elemento estructurante para la apertura morfológica: solo
# sobreviven trazos rectos de al menos max(25, lado // 12) píxeles, es decir,
# las líneas de la grilla y no los dígitos.
LARGO_LINEA_MIN = 25
DIVISOR_LARGO_LINEA = 12

# Alrededor de cada posición esperada de línea (k·lado/n) se busca el máximo
# del perfil en un radio de max(4, 9% del tamaño de celda) píxeles.
RADIO_BUSQUEDA_MIN = 4
FRACCION_RADIO_BUSQUEDA = 0.09

# Puntaje de cada n = promedio + PESO_MINIMO·mínimo + PESO_N·n, sobre los
# valores del perfil en las líneas internas esperadas.
#   - el promedio premia que las líneas estén donde se esperan;
#   - el mínimo castiga que falte aunque sea una línea;
#   - el término en n desempata a favor del n mayor, porque un 6×6 también
#     tiene líneas en las posiciones de un 3×3.
PESO_MINIMO = 0.2
PESO_N = 0.015

# Se rechaza la cuadrícula si alguna línea esperada tiene menos de LINEA_MIN
# de cobertura o si el puntaje total queda bajo PUNTAJE_MIN.
LINEA_MIN = 0.10
PUNTAJE_MIN = 0.32

# =============================================================================
# --- Celdas --- (celdas.py: separar blancas de pistas)
# =============================================================================

# Interior de la celda que se mira (del 20% al 80%), para no tomar las líneas.
MARGEN_INTERIOR_INICIO = 0.2
MARGEN_INTERIOR_FIN = 0.8

# Normalización de iluminación: un cierre con kernel de max(3, paso // 3)
# borra los dígitos; una dilatación de (3·paso + 1) estima el fondo claro de
# la zona y un gaussiano de sigma paso/2 lo suaviza.
KERNEL_FONDO_MIN = 3
DIVISOR_KERNEL_FONDO = 3
FACTOR_VENTANA_ILUMINACION = 3
DIVISOR_SIGMA_ILUMINACION = 2

# Si la diferencia entre la celda más clara y la más oscura es menor que
# esto (0-255), no hay forma de separar blancas de oscuras.
CONTRASTE_MIN = 15

# Detección de la diagonal de una celda de pista.
KERNEL_DESENFOQUE_DIAGONAL = (5, 5)
CANNY_DIAGONAL = (35, 110)
# HoughLinesP: resolución angular pi/180 (1°), votos mínimos max(12, h // 5),
# largo mínimo 65% del alto de la celda y hueco máximo 8%.
DIAGONAL_DIVISOR_ANGULO = 180
DIAGONAL_UMBRAL_MIN = 12
DIAGONAL_DIVISOR_UMBRAL = 5
DIAGONAL_LARGO_MIN = 0.65
DIAGONAL_HUECO_MAX = 0.08
# La línea debe bajar hacia la derecha con pendiente entre 0.8 y 1.25 (~45°)
# y su punto medio debe estar a menos del 7% de la diagonal principal.
DIAGONAL_PENDIENTE_MIN = 0.8
DIAGONAL_PENDIENTE_MAX = 1.25
DIAGONAL_DISTANCIA_MAX = 0.07

# Una celda también es blanca si su fondo es más claro que el de la celda
# oscura más cercana por al menos max(8, 10% de ese fondo).
MARGEN_FONDO_MIN = 8
MARGEN_FONDO_RELATIVO = 0.10

# =============================================================================
# --- OCR --- (ocr.py: preparar números, leer pistas, filtro de bandas)
# =============================================================================

# Filtro de bandas (moiré): en el espectro centrado se atenúan las franjas de
# ANCHO_BANDA píxeles sobre los ejes, fuera de un radio max(12, 2·n) que
# conserva las frecuencias bajas. Se multiplica por ATENUACION_BANDAS.
ANCHO_BANDA = 3
RADIO_BANDAS_MIN = 12
FACTOR_RADIO_BANDAS = 2
ATENUACION_BANDAS = 0.03

# Normalización opcional del fondo de la pista: se divide por un gaussiano de
# KERNEL_FONDO_LOCAL_ANCHO × max(15, h // 2) (impar) y se escala a 160.
KERNEL_FONDO_LOCAL_ANCHO = 3
KERNEL_FONDO_LOCAL_ALTO_MIN = 15
DIVISOR_FONDO_LOCAL = 2
ESCALA_NORMALIZACION_OCR = 160

# Máscara triangular. La celda de pista está partida por su diagonal:
#   - la suma "derecha" está en el triángulo de arriba a la derecha (y < x);
#   - la suma "abajo" está en el triángulo de abajo a la izquierda (y > x).
# Se deja un margen de 3.5% (MARGEN_MASCARA_INICIO/_FIN) en el borde de la celda, una franja de
# DESPLAZAMIENTO_DIAGONAL a cada lado de la diagonal (para no tomar la línea)
# y se limita la mitad vertical correspondiente.
MARGEN_MASCARA_INICIO = 0.035
MARGEN_MASCARA_FIN = 0.965
DESPLAZAMIENTO_DIAGONAL = 0.09
LIMITE_Y_DERECHA = 0.52
LIMITE_Y_ABAJO = 0.48

# Zona central (12%-88%) para estimar el fondo de la celda de pista.
MARGEN_FONDO_OCR_INICIO = 0.12
MARGEN_FONDO_OCR_FIN = 0.88
# Si ese fondo es menor que esto, la celda es oscura con dígitos claros.
FONDO_OSCURO = 100

KERNEL_DESENFOQUE_OCR = (3, 3)

# Bloque del umbral adaptativo: tercio del lado menor, impar, entre 15 y 51.
BLOQUE_OCR_MIN = 15
BLOQUE_OCR_MAX = 51
DIVISOR_BLOQUE_OCR = 3
# Constante por defecto del umbral adaptativo.
CONSTANTE_OCR = 7

# Un componente conexo es un dígito si su alto está entre 8.5% y 48% de la
# celda, su ancho entre 0.8% y 38%, y su área es al menos 0.08% de la celda.
ALTO_DIGITO_MIN = 0.085
ALTO_DIGITO_MAX = 0.48
ANCHO_DIGITO_MIN = 0.008
ANCHO_DIGITO_MAX = 0.38
AREA_DIGITO_MIN = 0.0008
# Se descartan componentes más bajos que el 55% del más alto (manchas).
ALTURA_RELATIVA_MIN = 0.55

# El número recortado se escala a este alto (px) y se le agrega un borde
# blanco, que es como Tesseract lee mejor.
ALTURA_OBJETIVO = 64
BORDE_OCR = 16

# Intentos de binarización: (normalizar, adaptativa, invertir, constante).
# Lectura normal: las 8 combinaciones, en este orden; se corta antes si ya
# hay una lectura confiable.
INTENTOS_NORMALES = [
    (False, False, False, 7),
    (False, False, True, 7),
    (False, True, False, 7),
    (False, True, True, 7),
    (True, False, False, 7),
    (True, False, True, 7),
    (True, True, False, 7),
    (True, True, True, 7),
]
# Relectura tras el filtro de bandas: umbral adaptativo con 3 constantes,
# con y sin invertir. Se hacen todos.
INTENTOS_REFORZADOS = [
    (False, True, False, 7),
    (False, True, True, 7),
    (False, True, False, 14),
    (False, True, True, 14),
    (False, True, False, 21),
    (False, True, True, 21),
]

# Píxel de tinta en la imagen preparada (negro sobre blanco).
UMBRAL_TINTA = 128
# Un componente cuenta como dígito completo si mide al menos esto en alto y
# área (px, sobre la imagen escalada a ALTURA_OBJETIVO).
ALTO_DIGITO_PREPARADO = 35
AREA_DIGITO_PREPARADO = 35
# Si se ven 2 dígitos y Tesseract lee 2 cifras, el voto vale más.
VOTO_NORMAL = 1
VOTO_DOS_DIGITOS = 3

# Tesseract: motor LSTM, modos de página 7 (línea), 8 (palabra) y 13 (línea
# cruda), solo dígitos y tiempo máximo por llamada en segundos.
OEM = 1
PSM_OCR = (7, 8, 13)
LISTA_BLANCA_OCR = "0123456789"
TIEMPO_MAXIMO_OCR = 5

# Una lectura válida es un número de 1 o 2 cifras entre 1 y 45 (1+2+...+9).
PATRON_PISTA = r"\d{1,2}"
SUMA_MIN = 1
SUMA_MAX = 45

# Se deja de probar intentos cuando el más votado tiene al menos VOTOS_PARA_PARAR
# votos y, o bien ya se usó normalización, o alguna confianza llega a CONFIANZA_MIN.
VOTOS_PARA_PARAR = 2
CONFIANZA_MIN = 35

# Cuántos candidatos se devuelven por pista.
MAX_CANDIDATOS = 4

# =============================================================================
# --- Estructura --- (estructura.py)
# =============================================================================

# Un grupo (suma) de Kakuro tiene al menos 2 celdas.
LONGITUD_MINIMA_GRUPO = 2

# =============================================================================
# --- Modelo CP --- (modelo_cp.py)
# =============================================================================

# Dominio de cada celda blanca.
DIGITO_MIN = 1
DIGITO_MAX = 9

# Costo extra de una suma obtenida cambiando un dígito según CONFUSIONES.
# Como el ranking de candidatos va de 0 a 3, cualquier lectura directa del
# OCR cuesta menos que cualquier variante por confusión.
COSTO_CONFUSION = 10

# Valor inicial al buscar el menor costo de una suma; funciona como infinito.
COSTO_INICIAL = 999

# Parámetros de CP-SAT. Semilla fija y un solo hilo hacen que el resultado
# sea siempre el mismo cuando hay varias soluciones de igual costo.
TIEMPO_LIMITE = 15
SEMILLA = 0
HILOS = 1

# =============================================================================
# --- Visualización --- (visualizacion.py)
# =============================================================================

# La escala del texto es el tamaño de celda dividido por esto.
DIVISOR_ESCALA_TEXTO = 110
GROSOR_TEXTO = 2
COLOR_SOLUCION = (0, 0, 0)  # BGR

