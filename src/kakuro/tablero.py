"""Tablero: localizar el Kakuro en la imagen y corregir la perspectiva."""

import cv2
import numpy as np

from . import config
from .cuadricula import detectar_cuadricula


def ordenar_puntos(puntos):
    """Ordena las 4 esquinas de un cuadrilátero.

    Recibe 4 puntos (x, y) en cualquier orden y en cualquier forma que se
    pueda llevar a (4, 2). Devuelve un arreglo float32 de (4, 2) en este
    orden: arriba-izquierda, arriba-derecha, abajo-derecha, abajo-izquierda.

    Arriba-izquierda tiene la menor x+y y abajo-derecha la mayor; con y-x,
    arriba-derecha tiene el menor valor y abajo-izquierda el mayor.
    """
    puntos = np.asarray(puntos, np.float32).reshape(4, 2)
    suma = puntos.sum(axis=1)
    resta = np.diff(puntos, axis=1).ravel()
    return puntos[[np.argmin(suma), np.argmin(resta), np.argmax(suma), np.argmax(resta)]]


# -----------------------------------------------------------------------------
# Respaldo: buscar el borde del tablero con líneas de Hough
# -----------------------------------------------------------------------------


def detectar_segmentos(gris):
    """Busca segmentos de línea largos con Hough, con dos niveles de suavizado.

    Recibe la imagen en gris (ya reducida y suavizada por rectificar_tablero).
    Devuelve un arreglo de (k, 4) con (x1, y1, x2, y2) por segmento, o None
    si no se encontró ninguno.
    """
    h, w = gris.shape
    lista = []
    for sigma in config.SIGMAS_HOUGH:
        suave = cv2.GaussianBlur(gris, (0, 0), sigma)
        bordes = cv2.Canny(suave, *config.CANNY_HOUGH)
        detectadas = cv2.HoughLinesP(
            bordes,
            config.HOUGH_RESOLUCION_RHO,
            np.pi / config.HOUGH_DIVISOR_ANGULO,
            threshold=config.HOUGH_UMBRAL,
            minLineLength=min(h, w) * config.HOUGH_LARGO_MIN,
            maxLineGap=config.HOUGH_HUECO_MAX,
        )
        if detectadas is not None:
            lista.extend(detectadas.reshape(-1, 4))
    return np.array(lista) if lista else None


def agrupar_lineas(segmentos, h, w):
    """Separa los segmentos en horizontales y verticales y quita repetidos.

    Cada segmento se pasa a una recta normalizada (a, b, c) con a·x + b·y + c = 0.
    Las diagonales se ignoran. Dentro de cada familia se recorre de la línea
    más larga a la más corta y se descarta una línea si ya hay otra con centro
    y dirección casi iguales.

    Recibe los segmentos (salida de detectar_segmentos) y el alto y ancho de
    la imagen. Devuelve una lista [horizontales, verticales]; cada una es una
    lista de hasta MAX_LINEAS_FAMILIA tuplas (largo, centro, recta), donde
    centro es la altura (horizontales) o la abscisa (verticales) de la recta
    en el medio de la imagen.
    """
    familias = [[], []]
    for x1, y1, x2, y2 in segmentos.reshape(-1, 4):
        dx, dy = x2 - x1, y2 - y1
        largo = np.hypot(dx, dy)
        if abs(dy) < config.PENDIENTE_MAX_FAMILIA * abs(dx):
            tipo = 0
        elif abs(dx) < config.PENDIENTE_MAX_FAMILIA * abs(dy):
            tipo = 1
        else:
            continue
        linea = np.array([y1 - y2, x2 - x1, x1 * y2 - x2 * y1], float) / largo
        # Se orienta la normal siempre igual para poder comparar rectas.
        if linea[tipo ^ 1] < 0:
            linea = -linea
        centro = (
            -(linea[0] * w / 2 + linea[2]) / linea[1]
            if tipo == 0
            else -(linea[1] * h / 2 + linea[2]) / linea[0]
        )
        familias[tipo].append((largo, centro, linea))
    grupos = []
    for familia in familias:
        unicas = []
        for largo, centro, linea in sorted(familia, key=lambda t: t[0], reverse=True):
            if not any(
                abs(centro - c) < config.DISTANCIA_CENTRO_REPETIDA
                and np.linalg.norm(linea[:2] - l[:2]) < config.DIFERENCIA_NORMAL_REPETIDA
                for _, c, l in unicas
            ):
                unicas.append((largo, centro, linea))
        grupos.append(unicas[:config.MAX_LINEAS_FAMILIA])
    return grupos


def interseccion(a, b):
    """Punto donde se cortan dos rectas en coordenadas homogéneas.

    Recibe dos rectas (a, b, c). Devuelve el punto (x, y) como arreglo, o
    PUNTO_SIN_INTERSECCION (muy lejos de la imagen) si son paralelas.
    """
    p = np.cross(a, b)
    return p[:2] / p[2] if abs(p[2]) > config.TOLERANCIA_PARALELAS else np.array(config.PUNTO_SIN_INTERSECCION)


def armar_cuadrilateros(familias, h, w):
    """Arma cuadriláteros cruzando 2 líneas horizontales con 2 verticales.

    Solo usa parejas de líneas paralelas bien separadas (más de
    SEPARACION_MIN_PAREJA del alto o ancho). Se queda con los cuadriláteros
    que caben en la imagen y cuya área está entre AREA_MIN_HOUGH y
    AREA_MAX_HOUGH.

    Recibe [horizontales, verticales] (salida de agrupar_lineas) y el alto y
    ancho de la imagen. Devuelve una lista de hasta MAX_CANDIDATOS_HOUGH
    tuplas (area, esquinas), de mayor a menor área.
    """
    parejas = []
    for tipo, familia in enumerate(familias):
        parejas.append(
            [
                (a, b)
                for i, a in enumerate(familia)
                for b in familia[i + 1:]
                if abs(a[1] - b[1]) > config.SEPARACION_MIN_PAREJA * (h if tipo == 0 else w)
            ]
        )
    candidatos = []
    for ha, hb in parejas[0]:
        for va, vb in parejas[1]:
            q = ordenar_puntos(
                [
                    interseccion(ha[2], va[2]),
                    interseccion(ha[2], vb[2]),
                    interseccion(hb[2], va[2]),
                    interseccion(hb[2], vb[2]),
                ]
            )
            area = cv2.contourArea(q)
            if (
                config.AREA_MIN_HOUGH * h * w < area < config.AREA_MAX_HOUGH * h * w
                and np.all(q >= 0)
                and np.all(q[:, 0] < w)
                and np.all(q[:, 1] < h)
            ):
                # El soporte (largo total de las 4 líneas) se guarda pero hoy
                # no se usa: el orden final es solo por área.
                soporte = sum(t[0] for t in (ha, hb, va, vb))
                candidatos.append((soporte, area, q))
    return [(area, q) for _, area, q in sorted(candidatos, key=lambda t: t[1], reverse=True)[:config.MAX_CANDIDATOS_HOUGH]]


def candidatos_por_lineas(gris):
    """Busca el borde del tablero a partir de líneas largas (respaldo con Hough).

    Se usa cuando ningún contorno sirvió, por ejemplo si un objeto tapa parte
    del borde. Recibe la imagen en gris reducida y suavizada. Devuelve una
    lista de tuplas (area, esquinas) de mayor a menor área; vacía si no hay
    líneas.
    """
    h, w = gris.shape
    segmentos = detectar_segmentos(gris)
    if segmentos is None:
        return []
    familias = agrupar_lineas(segmentos, h, w)
    return armar_cuadrilateros(familias, h, w)


# -----------------------------------------------------------------------------
# Corrección de perspectiva
# -----------------------------------------------------------------------------


def probar_cuadrilatero(imagen, q, escala):
    """Rectifica la imagen con un cuadrilátero y comprueba si tiene una grilla.

    Recibe la imagen original (BGR), las 4 esquinas q medidas en la imagen
    reducida y la escala de esa reducción.
    Devuelve una tupla (puntaje, rectificada, n, lx, ly) si
    detectar_cuadricula encuentra una grilla, o None si no.
    """
    destino = np.float32([[0, 0], [config.LADO - 1, 0], [config.LADO - 1, config.LADO - 1], [0, config.LADO - 1]])
    matriz = cv2.getPerspectiveTransform(q / escala, destino)
    rectificada = cv2.warpPerspective(imagen, matriz, (config.LADO, config.LADO))
    try:
        n, lx, ly, puntaje = detectar_cuadricula(rectificada)
    except ValueError:
        return None
    return puntaje, rectificada, n, lx, ly


def rectificar_tablero(imagen):
    """Encuentra el tablero en la imagen y lo lleva a una vista frontal cuadrada.

    1. Reduce la imagen y busca contornos de 4 lados en 3 mapas (Canny,
       Canny con CLAHE y umbral adaptativo).
    2. Prueba los MAX_CUADRILATEROS de mayor área: rectifica cada uno y se
       queda con los que tienen una grilla válida.
    3. Si ninguno sirvió, usa el respaldo con líneas de Hough y, entre los
       candidatos con buen puntaje, elige el de mayor área.
    4. Devuelve el de mayor puntaje (y a igual puntaje, mayor área).

    Recibe la imagen original (BGR).
    Devuelve una tupla (rectificada, n, lx, ly, puntaje):
      - rectificada: imagen BGR de LADO×LADO;
      - n, lx, ly, puntaje: como en cuadricula.detectar_cuadricula.
    Lanza ValueError si no encuentra el tablero completo.
    """
    alto, ancho = imagen.shape[:2]
    escala = min(1, config.ESCALA_MAX / max(alto, ancho))
    pequena = cv2.resize(imagen, None, fx=escala, fy=escala) if escala < 1 else imagen
    gris = cv2.cvtColor(pequena, cv2.COLOR_BGR2GRAY)
    gris = cv2.GaussianBlur(gris, config.KERNEL_DESENFOQUE_TABLERO, 0)
    realzada = cv2.createCLAHE(clipLimit=config.CLAHE_LIMITE, tileGridSize=config.CLAHE_CUADRICULA).apply(gris)
    mapas = [
        cv2.Canny(gris, *config.CANNY_TABLERO_GRIS),
        cv2.Canny(realzada, *config.CANNY_TABLERO_REALZADA),
        cv2.adaptiveThreshold(
            gris, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV,
            config.BLOQUE_ADAPTATIVO_TABLERO, config.CONSTANTE_ADAPTATIVA_TABLERO,
        ),
    ]
    cuadrilateros = []
    area_imagen = pequena.shape[0] * pequena.shape[1]
    for mapa in mapas:
        mapa = cv2.morphologyEx(mapa, cv2.MORPH_CLOSE, np.ones(config.KERNEL_CIERRE_TABLERO, np.uint8))
        contornos, _ = cv2.findContours(mapa, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for contorno in contornos:
            area = cv2.contourArea(contorno)
            if not config.AREA_MIN_TABLERO * area_imagen < area < config.AREA_MAX_TABLERO * area_imagen:
                continue
            perimetro = cv2.arcLength(contorno, True)
            for epsilon in config.EPSILONS_APROXIMACION:
                poligono = cv2.approxPolyDP(contorno, epsilon * perimetro, True)
                if len(poligono) == 4 and cv2.isContourConvex(poligono):
                    q = ordenar_puntos(poligono)
                    lados = np.linalg.norm(q - np.roll(q, 1, axis=0), axis=1)
                    # Demasiado alargado: se prueba con el siguiente epsilon.
                    if min(lados) / max(lados) < config.PROPORCION_LADOS_MIN:
                        continue
                    if not any(
                        np.mean(np.linalg.norm(q - q0, axis=1)) < config.DISTANCIA_CUADRILATERO_REPETIDO
                        for _, q0 in cuadrilateros
                    ):
                        cuadrilateros.append((area, q))
                    break
    cuadrilateros.sort(key=lambda x: x[0], reverse=True)
    mejores = []
    for area, q in cuadrilateros[:config.MAX_CUADRILATEROS]:
        prueba = probar_cuadrilatero(imagen, q, escala)
        if prueba is not None:
            puntaje, rectificada, n, lx, ly = prueba
            mejores.append((puntaje, area, rectificada, n, lx, ly))
    if not mejores:
        for area, q in candidatos_por_lineas(gris):
            prueba = probar_cuadrilatero(imagen, q, escala)
            if prueba is not None:
                puntaje, rectificada, n, lx, ly = prueba
                mejores.append((puntaje, area, rectificada, n, lx, ly))
        if mejores:
            # Elegimos el tablero completo para evitar un recorte de solo una parte.
            limite = config.FRACCION_PUNTAJE_RESPALDO * max(t[0] for t in mejores)
            mejores = [max((t for t in mejores if t[0] >= limite), key=lambda t: t[1])]
    if not mejores:
        raise ValueError(
            "No se pudo localizar el tablero completo. Usa una foto nítida con sus cuatro bordes visibles."
        )
    puntaje, _, rectificada, n, lx, ly = max(mejores, key=lambda x: (x[0], x[1]))
    return rectificada, n, lx, ly, puntaje
