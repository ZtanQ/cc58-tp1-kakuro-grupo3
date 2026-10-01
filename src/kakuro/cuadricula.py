"""Cuadrícula: detectar el tamaño n del tablero y la posición de sus líneas."""

import cv2
import numpy as np

from . import config


def proyecciones_lineas(imagen):
    """Calcula qué tanto aparece una línea de la grilla en cada columna y fila.

    Detecta bordes con Canny y aplica una apertura morfológica con un trazo
    largo horizontal y otro vertical: así sobreviven las líneas de la grilla
    y se borran los dígitos y la diagonal de las pistas.

    Recibe la imagen rectificada (BGR).
    Devuelve una tupla (px, py) de arreglos con valores entre 0 y 1:
      - px[x]: fracción de la columna x cubierta por líneas verticales;
      - py[y]: fracción de la fila y cubierta por líneas horizontales.
    """
    gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    gris = cv2.GaussianBlur(gris, config.KERNEL_DESENFOQUE_CUADRICULA, 0)
    bordes = cv2.Canny(gris, *config.CANNY_CUADRICULA)
    bordes = cv2.dilate(bordes, np.ones(config.KERNEL_DILATACION_CUADRICULA, np.uint8))
    largo = max(config.LARGO_LINEA_MIN, imagen.shape[0] // config.DIVISOR_LARGO_LINEA)
    horizontal = cv2.morphologyEx(
        bordes, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (largo, 1))
    )
    vertical = cv2.morphologyEx(
        bordes, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, largo))
    )
    return np.mean(vertical > 0, axis=0), np.mean(horizontal > 0, axis=1)


def detectar_cuadricula(imagen):
    """Encuentra el tamaño n de la grilla y la posición de cada línea.

    Para cada n entre MIN_N y MAX_N, busca cada línea interna cerca de donde
    debería estar (k·lado/n, con un radio de tolerancia) y toma el valor del
    perfil en ese punto. El puntaje de n es:

        promedio(valores) + PESO_MINIMO · mínimo(valores) + PESO_N · n

    El promedio premia que haya líneas donde se esperan; el mínimo castiga
    que falte alguna; el término en n desempata a favor del n mayor (un 6×6
    también tiene líneas donde las tendría un 3×3). Se queda con el n de
    mayor puntaje.

    Recibe la imagen rectificada (BGR, cuadrada).
    Devuelve una tupla (n, lx, ly, puntaje):
      - lx, ly: listas de n+1 posiciones (px) de las líneas verticales y
        horizontales, incluidos los dos bordes;
      - puntaje: el puntaje del n elegido.
    Lanza ValueError si alguna línea queda bajo LINEA_MIN o el puntaje bajo
    PUNTAJE_MIN.
    """
    px, py = proyecciones_lineas(imagen)
    candidatos = []
    for n in range(config.MIN_N, config.MAX_N + 1):
        valores, lineas = [], []
        for perfil in (px, py):
            posiciones = [0]
            for k in range(1, n):
                centro = k * (len(perfil) - 1) / n
                radio = max(config.RADIO_BUSQUEDA_MIN, round(len(perfil) / n * config.FRACCION_RADIO_BUSQUEDA))
                a, b = round(centro) - radio, round(centro) + radio + 1
                posicion = a + int(np.argmax(perfil[a:b]))
                posiciones.append(posicion)
                valores.append(float(perfil[posicion]))
            posiciones.append(len(perfil) - 1)
            lineas.append(posiciones)
        puntaje = np.mean(valores) + config.PESO_MINIMO * min(valores) + config.PESO_N * n
        candidatos.append((puntaje, min(valores), n, lineas))
    puntaje, minimo, n, lineas = max(candidatos, key=lambda x: x[0])
    if minimo < config.LINEA_MIN or puntaje < config.PUNTAJE_MIN:
        raise ValueError("No se encontró una cuadrícula regular suficientemente clara.")
    return n, lineas[0], lineas[1], float(puntaje)
