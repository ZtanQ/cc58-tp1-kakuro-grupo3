"""Estructura del tablero: grupos de celdas, su validación y exportación a JSON."""

import json
from collections import Counter

from . import config


def construir_grupos(blancas, pistas):
    """Arma los grupos (sumas) del Kakuro y revisa que cubran todo el tablero.

    Desde cada pista avanza a la derecha o hacia abajo mientras haya celdas
    blancas. Después revisa que cada celda blanca esté en exactamente un
    grupo horizontal y un grupo vertical.

    Recibe el set de celdas blancas y las pistas leídas (salida de
    ocr.extraer_pistas).
    Devuelve una lista de diccionarios con "origen", "direccion", "celdas"
    (lista de (fila, columna)) y "ocr" (candidatos leídos).
    Lanza ValueError si no hay celdas blancas, si un grupo tiene menos de
    LONGITUD_MINIMA_GRUPO celdas o si alguna celda blanca no queda cubierta
    una vez en cada dirección.
    """
    if not blancas:
        raise ValueError(
            "No se detectaron celdas blancas; revisa la iluminación y el recorte del tablero."
        )
    grupos = []
    for origen, lecturas in pistas.items():
        for direccion, candidatos in lecturas.items():
            df, dc = (0, 1) if direccion == "derecha" else (1, 0)
            f, c = origen[0] + df, origen[1] + dc
            celdas = []
            while (f, c) in blancas:
                celdas.append((f, c))
                f += df
                c += dc
            if len(celdas) < config.LONGITUD_MINIMA_GRUPO:
                raise ValueError(f"Grupo incompleto en {origen}, {direccion}.")
            grupos.append(
                {"origen": origen, "direccion": direccion, "celdas": celdas, "ocr": candidatos}
            )
    cobertura = Counter((celda, g["direccion"]) for g in grupos for celda in g["celdas"])
    if any(cobertura[(celda, d)] != 1 for celda in blancas for d in ("derecha", "abajo")):
        raise ValueError("La segmentación no forma grupos horizontales y verticales completos.")
    return grupos


def exportar_json(resultado, ruta=None, nombre_imagen=None):
    """Exporta el estado inicial leído de la imagen con el formato de data/ground_truth/.

    El estado inicial es lo que el sistema entendió antes de resolver:
      - "n": tamaño del tablero;
      - "celdas_blancas": lista de [fila, columna], ordenada;
      - "pistas": lista de {"origen": [fila, columna], "derecha": suma o null,
        "abajo": suma o null}, ordenada por origen, con el primer candidato
        del OCR de cada dirección;
      - "pistas_sin_lectura": lista de [fila, columna, direccion] de las
        pistas que el OCR no pudo leer. En "pistas" aparecen como null, así
        que esta lista es la que distingue "no hay pista" de "no se leyó".
    No incluye la solución. Si se pasa `nombre_imagen`, se agrega "imagen".

    Recibe el Resultado de pipeline.procesar_imagen (o su a_dict()), la ruta
    donde guardar el archivo (opcional) y el nombre de la imagen (opcional).
    Devuelve el diccionario exportado; si hay `ruta`, también lo guarda en
    UTF-8 con sangría de 2 espacios.
    Lanza ValueError si el resultado no llegó a leer las pistas (falló en
    la etapa del tablero o de las celdas).
    """
    datos = resultado.a_dict() if hasattr(resultado, "a_dict") else resultado
    if datos.get("pistas") is None or datos.get("blancas") is None:
        raise ValueError(
            f"No hay estado inicial para exportar: el pipeline falló en la etapa "
            f"'{datos.get('error_etapa', '?')}' ({datos.get('error', 'sin mensaje')})."
        )
    estado = {}
    if nombre_imagen is not None:
        estado["imagen"] = nombre_imagen
    estado["n"] = datos["n"]
    estado["celdas_blancas"] = [list(celda) for celda in sorted(datos["blancas"])]
    pistas, sin_lectura = [], []
    for (fila, columna), lecturas in sorted(datos["pistas"].items()):
        pista = {"origen": [fila, columna], "derecha": None, "abajo": None}
        for direccion, candidatos in lecturas.items():
            if candidatos:
                pista[direccion] = candidatos[0]
            else:
                sin_lectura.append([fila, columna, direccion])
        pistas.append(pista)
    estado["pistas"] = pistas
    estado["pistas_sin_lectura"] = sin_lectura
    if ruta is not None:
        with open(ruta, "w", encoding="utf-8") as archivo:
            json.dump(estado, archivo, ensure_ascii=False, indent=2)
    return estado
