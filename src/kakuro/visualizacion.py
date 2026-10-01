"""Dibujo de la solución sobre la imagen rectificada."""

import cv2

from . import config


def dibujar_solucion(resultado):
    """Escribe cada dígito de la solución centrado en su celda.

    Recibe el resultado de procesar_imagen como diccionario (Resultado.a_dict())
    con las claves "imagen", "lx", "ly" y "solucion". Si "solucion" es None,
    devuelve la imagen sin números.
    Devuelve una copia de la imagen con los dígitos dibujados.
    Lanza KeyError si el resultado no tiene "imagen" (el tablero no se encontró).
    """
    imagen = resultado["imagen"].copy()
    lx, ly = resultado["lx"], resultado["ly"]
    for (f, c), valor in (resultado["solucion"] or {}).items():
        texto = str(valor)
        paso = min(lx[c] - lx[c - 1], ly[f] - ly[f - 1])
        escala = paso / config.DIVISOR_ESCALA_TEXTO
        (w, h), _ = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, escala, config.GROSOR_TEXTO)
        x = (lx[c - 1] + lx[c] - w) // 2
        y = (ly[f - 1] + ly[f] + h) // 2
        cv2.putText(
            imagen, texto, (x, y), cv2.FONT_HERSHEY_SIMPLEX, escala,
            config.COLOR_SOLUCION, config.GROSOR_TEXTO, cv2.LINE_AA,
        )
    return imagen
