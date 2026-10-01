"""Celdas: recortar la grilla y separar las celdas blancas de las de pista."""

import cv2
import numpy as np

from . import config


def _interior(region):
    """Devuelve la zona central de una región (de MARGEN_INTERIOR_INICIO a _FIN)."""
    h, w = region.shape[:2]
    inicio, fin = config.MARGEN_INTERIOR_INICIO, config.MARGEN_INTERIOR_FIN
    return region[int(inicio * h):int(fin * h), int(inicio * w):int(fin * w)]


def recortar_celdas(imagen, n, lx, ly):
    """Recorta cada celda siguiendo las líneas detectadas de la grilla.

    Recibe la imagen rectificada (BGR), n y las posiciones de las líneas
    verticales (lx) y horizontales (ly), cada una con n+1 valores.
    Devuelve un diccionario {(fila, columna): recorte BGR}, con fila y
    columna empezando en 1.
    """
    return {
        (f + 1, c + 1): imagen[ly[f]:ly[f + 1], lx[c]:lx[c + 1]]
        for f in range(n)
        for c in range(n)
    }


def normalizar_iluminacion(gris, n):
    """Divide la imagen por una estimación del fondo para quitar sombras.

    Un cierre morfológico borra los dígitos, una dilatación grande toma el
    fondo más claro de la zona y un gaussiano lo suaviza. Al dividir, una
    celda blanca queda clara aunque esté en sombra.

    Recibe la imagen en gris y n (para saber el tamaño de celda).
    Devuelve la imagen normalizada (uint8, 0-255).
    """
    paso = round(gris.shape[0] / n)
    k = max(config.KERNEL_FONDO_MIN, paso // config.DIVISOR_KERNEL_FONDO)
    fondo = cv2.morphologyEx(gris, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    ventana = paso * config.FACTOR_VENTANA_ILUMINACION + 1
    iluminacion = cv2.dilate(fondo, np.ones((ventana, ventana), np.uint8))
    iluminacion = cv2.GaussianBlur(iluminacion, (0, 0), paso / config.DIVISOR_SIGMA_ILUMINACION)
    return cv2.divide(gris, np.maximum(iluminacion, 1), scale=255)


def tiene_diagonal(celda):
    """Indica si la celda tiene la diagonal que marca una celda de pista.

    Busca con Hough una línea larga que baje hacia la derecha a unos 45° y
    pase cerca de la diagonal principal de la celda.

    Recibe el recorte BGR de una celda. Devuelve True si encuentra la diagonal.
    """
    g = cv2.cvtColor(celda, cv2.COLOR_BGR2GRAY)
    h, w = g.shape
    bordes = cv2.Canny(cv2.GaussianBlur(g, config.KERNEL_DESENFOQUE_DIAGONAL, 0), *config.CANNY_DIAGONAL)
    lineas = cv2.HoughLinesP(
        bordes,
        1,
        np.pi / config.DIAGONAL_DIVISOR_ANGULO,
        threshold=max(config.DIAGONAL_UMBRAL_MIN, h // config.DIAGONAL_DIVISOR_UMBRAL),
        minLineLength=h * config.DIAGONAL_LARGO_MIN,
        maxLineGap=h * config.DIAGONAL_HUECO_MAX,
    )
    if lineas is not None:
        for x1, y1, x2, y2 in lineas.reshape(-1, 4):
            dx, dy = x2 - x1, y2 - y1
            if (
                dx * dy > 0
                and config.DIAGONAL_PENDIENTE_MIN < abs(dy / (dx or 1)) < config.DIAGONAL_PENDIENTE_MAX
                and abs((y1 + y2) / 2 - (x1 + x2) / 2) < config.DIAGONAL_DISTANCIA_MAX * h
            ):
                return True
    return False


def quitar_blancas_aisladas(blancas):
    """Quita celdas blancas que no forman un grupo horizontal y otro vertical.

    Toda celda blanca de un Kakuro tiene al menos una vecina blanca en su
    fila y otra en su columna. Se repite hasta que no quede ninguna aislada,
    porque quitar una puede dejar aislada a otra.

    Recibe el set de celdas blancas. Devuelve el set filtrado.
    """
    while True:
        aisladas = {
            p
            for p in blancas
            if not any((p[0], p[1] + d) in blancas for d in (-1, 1))
            or not any((p[0] + d, p[1]) in blancas for d in (-1, 1))
        }
        if not aisladas:
            break
        blancas -= aisladas
    return blancas


def segmentar_y_clasificar(imagen, n, lx, ly):
    """Recorta las celdas y decide cuáles son blancas.

    Una celda es oscura (pista o vacía) si está en la fila 1, en la columna 1
    o tiene diagonal. Suposición: la fila 1 y la columna 1 siempre son
    pistas, porque en todo Kakuro la primera fila y la primera columna solo
    contienen pistas o celdas vacías.

    Las demás celdas son blancas si:
      - su brillo normalizado supera el umbral de Otsu calculado sobre las
        n×n celdas, o
      - su fondo es claramente más claro que el de las celdas oscuras más
        cercanas (en distancia de tablero).
    Al final se quitan las blancas aisladas.

    Recibe la imagen rectificada (BGR), n, lx y ly.
    Devuelve una tupla (blancas, recortes):
      - blancas: set de (fila, columna);
      - recortes: diccionario {(fila, columna): recorte BGR}.
    Lanza ValueError si no hay contraste suficiente entre celdas.
    """
    recortes = recortar_celdas(imagen, n, lx, ly)
    normalizada = normalizar_iluminacion(cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY), n)
    valores = []
    for f in range(n):
        for c in range(n):
            region = normalizada[ly[f]:ly[f + 1], lx[c]:lx[c + 1]]
            valores.append(np.median(_interior(region)))
    valores = np.uint8(valores).reshape(n, n)
    umbral, _ = cv2.threshold(valores, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if int(valores.max()) - int(valores.min()) < config.CONTRASTE_MIN:
        raise ValueError("No se distinguen celdas blancas y oscuras con suficiente contraste.")
    fondos = np.zeros((n, n), np.float32)
    oscuras = set()
    for (f, c), celda in recortes.items():
        fondos[f - 1, c - 1] = np.median(_interior(cv2.cvtColor(celda, cv2.COLOR_BGR2GRAY)))
        if f == 1 or c == 1 or tiene_diagonal(celda):
            oscuras.add((f, c))
    blancas = set()
    for f in range(1, n + 1):
        for c in range(1, n + 1):
            if (f, c) in oscuras:
                continue
            # Fondo de referencia: el más oscuro entre las celdas oscuras más cercanas.
            distancia = min(max(abs(f - a), abs(c - b)) for a, b in oscuras)
            vecinos = [
                fondos[a - 1, b - 1] for a, b in oscuras if max(abs(f - a), abs(c - b)) == distancia
            ]
            referencia = min(vecinos)
            margen = max(config.MARGEN_FONDO_MIN, config.MARGEN_FONDO_RELATIVO * referencia)
            if valores[f - 1, c - 1] > umbral or fondos[f - 1, c - 1] > referencia + margen:
                blancas.add((f, c))
    blancas = quitar_blancas_aisladas(blancas)
    return blancas, recortes
