"""OCR: preparar los números de las pistas, leerlos con Tesseract y el filtro de bandas."""

import re
from collections import Counter

import cv2
import numpy as np
import pytesseract

from . import config


def filtrar_bandas(imagen, n):
    """Reduce las bandas (moiré) de la imagen con un filtro de frecuencias.

    Las "bandas" son franjas claras y oscuras que se repiten a lo largo de la
    imagen, por ejemplo al fotografiar una pantalla. En el espectro de Fourier
    aparecen como energía concentrada sobre el eje horizontal o el vertical,
    lejos del centro. El filtro elige el eje con más energía y la atenúa,
    conservando las frecuencias bajas (la forma general de la imagen).

    Recibe la imagen rectificada (BGR) y n. Devuelve la imagen filtrada (BGR).
    """
    gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY).astype(np.float32)
    h, w = gris.shape
    y, x = np.mgrid[:h, :w]
    espectro = np.fft.fftshift(np.fft.fft2(gris))
    # Conservamos las frecuencias bajas y reducimos las bandas que se repiten.
    limite = max(config.RADIO_BANDAS_MIN, config.FACTOR_RADIO_BANDAS * n)
    bandas = [
        (np.abs(y - h // 2) <= config.ANCHO_BANDA) & (np.abs(x - w // 2) > limite),
        (np.abs(x - w // 2) <= config.ANCHO_BANDA) & (np.abs(y - h // 2) > limite),
    ]
    mascara = max(bandas, key=lambda m: np.sum(np.abs(espectro[m]) ** 2))
    espectro[mascara] *= config.ATENUACION_BANDAS
    filtrada = np.real(np.fft.ifft2(np.fft.ifftshift(espectro)))
    filtrada = np.uint8(np.clip(filtrada, 0, 255))
    return cv2.cvtColor(filtrada, cv2.COLOR_GRAY2BGR)


def _mascara_triangular(h, w, direccion):
    """Máscara booleana (h, w) con la zona donde está la suma de una dirección.

    La celda de pista está partida por su diagonal (de arriba-izquierda a
    abajo-derecha). En coordenadas normalizadas xn, yn entre 0 y 1:
      - "derecha": triángulo superior derecho, yn < xn - DESPLAZAMIENTO_DIAGONAL
        y yn < LIMITE_Y_DERECHA;
      - "abajo": triángulo inferior izquierdo, yn > xn + DESPLAZAMIENTO_DIAGONAL
        y yn > LIMITE_Y_ABAJO.
    Además se excluye un margen en los cuatro bordes (MARGEN_MASCARA_INICIO/_FIN). El
    desplazamiento deja fuera la línea diagonal misma.
    """
    y, x = np.mgrid[:h, :w]
    xn, yn = x / w, y / h
    m0, m1 = config.MARGEN_MASCARA_INICIO, config.MARGEN_MASCARA_FIN
    mascara = (xn > m0) & (xn < m1) & (yn > m0) & (yn < m1)
    d = config.DESPLAZAMIENTO_DIAGONAL
    mascara &= (yn < xn - d) if direccion == "derecha" else (yn > xn + d)
    mascara &= (yn < config.LIMITE_Y_DERECHA) if direccion == "derecha" else (yn > config.LIMITE_Y_ABAJO)
    return mascara


def preparar_numero(
    celda, direccion, adaptativa=False, invertir=False, normalizar=False, constante=config.CONSTANTE_OCR
):
    """Aísla el número de una pista y lo deja negro sobre blanco para Tesseract.

    Pasos: (opcional) normalizar el fondo, binarizar (Otsu o adaptativo, con
    o sin invertir), quedarse solo con la máscara triangular de la dirección,
    filtrar componentes conexos por tamaño, recortar, escalar a
    ALTURA_OBJETIVO y agregar un borde blanco.

    Recibe:
      - celda: recorte BGR de la celda de pista;
      - direccion: "derecha" o "abajo";
      - adaptativa: usar umbral adaptativo en vez de Otsu;
      - invertir: invertir la polaridad elegida automáticamente;
      - normalizar: dividir por el fondo local antes de binarizar;
      - constante: constante del umbral adaptativo.
    Devuelve la imagen preparada (uint8, número negro sobre blanco), o None si
    no quedó ningún componente con tamaño de dígito.
    """
    gris = cv2.cvtColor(celda, cv2.COLOR_BGR2GRAY)
    h, w = gris.shape
    if normalizar:
        # Ajustamos el fondo para reducir bandas y cambios de luz.
        alto_kernel = max(config.KERNEL_FONDO_LOCAL_ALTO_MIN, h // config.DIVISOR_FONDO_LOCAL) | 1
        fondo_local = cv2.GaussianBlur(gris, (config.KERNEL_FONDO_LOCAL_ANCHO, alto_kernel), 0)
        gris = cv2.divide(gris, np.maximum(fondo_local, 1), scale=config.ESCALA_NORMALIZACION_OCR)
    mascara = _mascara_triangular(h, w, direccion)
    i, j = config.MARGEN_FONDO_OCR_INICIO, config.MARGEN_FONDO_OCR_FIN
    fondo = float(np.median(gris[int(i * h):int(j * h), int(i * w):int(j * w)]))
    base = cv2.GaussianBlur(gris, config.KERNEL_DESENFOQUE_OCR, 0)
    # La tinta debe quedar en blanco (255): en fondo oscuro, BINARY; en claro, BINARY_INV.
    modo = cv2.THRESH_BINARY if fondo < config.FONDO_OSCURO else cv2.THRESH_BINARY_INV
    if invertir:
        modo = cv2.THRESH_BINARY_INV if modo == cv2.THRESH_BINARY else cv2.THRESH_BINARY
    if adaptativa:
        bloque = max(config.BLOQUE_OCR_MIN, min(config.BLOQUE_OCR_MAX, (min(h, w) // config.DIVISOR_BLOQUE_OCR) | 1))
        tinta = cv2.adaptiveThreshold(
            base,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            modo,
            bloque,
            -constante if fondo < config.FONDO_OSCURO else constante,
        )
    else:
        tinta = cv2.threshold(base, 0, 255, modo + cv2.THRESH_OTSU)[1]
    tinta[~mascara] = 0
    cantidad, etiquetas, estadisticas, _ = cv2.connectedComponentsWithStats(tinta)
    componentes = []
    for k in range(1, cantidad):
        cx, cy, cw, ch, area = estadisticas[k]
        if (
            config.ALTO_DIGITO_MIN * h <= ch <= config.ALTO_DIGITO_MAX * h
            and config.ANCHO_DIGITO_MIN * w <= cw <= config.ANCHO_DIGITO_MAX * w
            and area >= h * w * config.AREA_DIGITO_MIN
        ):
            componentes.append((k, cx, cy, cw, ch, area))
    if not componentes:
        return None
    # Quitamos manchas pequeñas comparadas con los números.
    altura = max(c[4] for c in componentes)
    componentes = [c for c in componentes if c[4] >= config.ALTURA_RELATIVA_MIN * altura]
    seleccion = np.isin(etiquetas, [c[0] for c in componentes])
    ys, xs = np.where(seleccion)
    numero = (255 - 255 * seleccion.astype(np.uint8))[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    factor = config.ALTURA_OBJETIVO / numero.shape[0]
    numero = cv2.resize(numero, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)
    b = config.BORDE_OCR
    return cv2.copyMakeBorder(numero, b, b, b, b, cv2.BORDER_CONSTANT, value=255)


def leer_pista(celda, direccion, reforzado=False):
    """Lee la suma de una pista combinando varias binarizaciones y modos de Tesseract.

    Cada intento (INTENTOS_NORMALES o INTENTOS_REFORZADOS) prepara el número
    de otra forma y lo lee con cada PSM de PSM_OCR. Cada lectura válida
    (1 a 45) suma un voto; vale VOTO_DOS_DIGITOS si se ven 2 dígitos y se
    leyeron 2 cifras. En la lectura normal se corta antes cuando ya hay una
    lectura con suficientes votos y confianza. En la reforzada se hacen
    todos los intentos.

    Recibe el recorte BGR de la celda, la dirección ("derecha" o "abajo") y si
    es la relectura tras el filtro de bandas.
    Devuelve hasta MAX_CANDIDATOS sumas, de más a menos votos (a igual votos,
    mayor confianza primero). Lista vacía si no se leyó nada.
    """
    votos, confianza = Counter(), {}
    intentos = config.INTENTOS_REFORZADOS if reforzado else config.INTENTOS_NORMALES
    for normalizar, adaptativa, invertir, constante in intentos:
        numero = preparar_numero(celda, direccion, adaptativa, invertir, normalizar, constante)
        if numero is None:
            continue
        _, _, componentes, _ = cv2.connectedComponentsWithStats(np.uint8(numero < config.UMBRAL_TINTA))
        dos_digitos = sum(
            ch >= config.ALTO_DIGITO_PREPARADO and area >= config.AREA_DIGITO_PREPARADO
            for _, _, cw, ch, area in componentes[1:]
        ) == 2
        for psm in config.PSM_OCR:
            datos = pytesseract.image_to_data(
                numero,
                output_type=pytesseract.Output.DICT,
                config=f"--oem {config.OEM} --psm {psm} -c tessedit_char_whitelist={config.LISTA_BLANCA_OCR}",
                timeout=config.TIEMPO_MAXIMO_OCR,
            )
            indices = [i for i, t in enumerate(datos["text"]) if str(t).strip()]
            texto = "".join(str(datos["text"][i]).strip() for i in indices)
            if re.fullmatch(config.PATRON_PISTA, texto) and config.SUMA_MIN <= int(texto) <= config.SUMA_MAX:
                valor = int(texto)
                votos[valor] += config.VOTO_DOS_DIGITOS if dos_digitos and len(texto) == 2 else config.VOTO_NORMAL
                conf = max([float(datos["conf"][i]) for i in indices], default=0)
                confianza[valor] = max(confianza.get(valor, 0), conf)
        if (
            not reforzado
            and votos
            and votos.most_common(1)[0][1] >= config.VOTOS_PARA_PARAR
            and (normalizar or max(confianza.values()) >= config.CONFIANZA_MIN)
        ):
            break
    return sorted(votos, key=lambda v: (votos[v], confianza[v]), reverse=True)[:config.MAX_CANDIDATOS]


def extraer_pistas(recortes, blancas, reforzado=False):
    """Lee todas las pistas del tablero.

    Una celda no blanca es pista "derecha" si tiene una blanca a su derecha y
    pista "abajo" si tiene una blanca debajo. Solo se leen las direcciones
    que hacen falta.

    Recibe los recortes de todas las celdas, el set de blancas y si es la
    relectura reforzada.
    Devuelve {(fila, columna): {"derecha": [...], "abajo": [...]}}, con solo
    las direcciones que aplican. Una lista vacía significa que no se leyó.
    """
    pistas = {}
    for (f, c), celda in recortes.items():
        if (f, c) in blancas:
            continue
        lecturas = {}
        if (f, c + 1) in blancas:
            lecturas["derecha"] = leer_pista(celda, "derecha", reforzado)
        if (f + 1, c) in blancas:
            lecturas["abajo"] = leer_pista(celda, "abajo", reforzado)
        if lecturas:
            pistas[(f, c)] = lecturas
    return pistas
