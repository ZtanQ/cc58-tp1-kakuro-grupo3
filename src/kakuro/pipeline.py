"""Punto de entrada: de una imagen de Kakuro a su solución.

Uso desde la terminal (con src/ en el PYTHONPATH):

    python -m kakuro.pipeline data/original/L_kakuro_07x07_clasico_01.png
    python -m kakuro.pipeline imagen.png --salida resuelto.png --json estado.json
"""

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any

import cv2
import numpy as np

from .celdas import recortar_celdas, segmentar_y_clasificar
from .estructura import construir_grupos, exportar_json
from .modelo_cp import resolver_csp
from .ocr import extraer_pistas, filtrar_bandas
from .tablero import rectificar_tablero
from .visualizacion import dibujar_solucion

# Marca de "campo todavía no asignado". Se distingue de None porque algunos
# campos (solucion, tiempo_solver_s...) sí pueden valer None.
FALTA = object()


def _campo():
    """Campo de Resultado que empieza sin asignar."""
    return field(default=FALTA)


@dataclass
class Resultado:
    """Salida de procesar_imagen. Un campo solo existe si se asignó.

    Siempre presentes:
      - estado: "NO_EJECUTADO", "PISTAS_SIN_LECTURA", "PISTAS_FUERA_DE_RANGO"
        o el estado de CP-SAT ("OPTIMAL", "FEASIBLE", "INFEASIBLE", ...).
      - solucion: {(fila, columna): dígito}, o None.
      - vision_ok: True si se llegó a leer las pistas.
      - tiempo_vision_s, tiempo_total_s: segundos.
    Tablero: imagen (rectificada, o filtrada si se usó el reintento), n, lx, ly,
      puntaje_cuadricula.
    Celdas y OCR: blancas, pistas.
    Estructura: grupos.
    Solver: tiempo_modelo_s, tiempo_solver_s, ramas, conflictos, penalizacion,
      sumas, busquedas_cp (cuántas veces se llamó a CP-SAT).
    Reintento con filtro de bandas: reintento_bandas, estado_inicial,
      estado_reintento.
    ajustes: lista de (origen, direccion, candidatos, suma) donde la suma
      usada no es el primer candidato del OCR (solo si hay solución).
    error, error_etapa: mensaje y etapa ("tablero", "clasificacion", "ocr",
      "grupos", "solver" o "relectura") si algo falló.
    """

    estado: Any = "NO_EJECUTADO"
    solucion: Any = None
    vision_ok: Any = False
    imagen: Any = _campo()
    n: Any = _campo()
    lx: Any = _campo()
    ly: Any = _campo()
    puntaje_cuadricula: Any = _campo()
    blancas: Any = _campo()
    pistas: Any = _campo()
    tiempo_vision_s: Any = _campo()
    grupos: Any = _campo()
    tiempo_modelo_s: Any = _campo()
    tiempo_solver_s: Any = _campo()
    ramas: Any = _campo()
    conflictos: Any = _campo()
    penalizacion: Any = _campo()
    sumas: Any = _campo()
    busquedas_cp: Any = _campo()
    reintento_bandas: Any = _campo()
    estado_inicial: Any = _campo()
    estado_reintento: Any = _campo()
    ajustes: Any = _campo()
    error: Any = _campo()
    error_etapa: Any = _campo()
    tiempo_total_s: Any = _campo()

    def __setattr__(self, nombre, valor):
        """Guarda el valor y recuerda el orden en que se asignó cada campo."""
        if not hasattr(self, "_orden"):
            object.__setattr__(self, "_orden", [])
        if valor is not FALTA and nombre not in self._orden:
            self._orden.append(nombre)
        object.__setattr__(self, nombre, valor)

    def tiene(self, nombre):
        """True si el campo `nombre` ya fue asignado."""
        return getattr(self, nombre) is not FALTA

    def obtener(self, nombre, defecto=None):
        """Valor del campo, o `defecto` si no fue asignado (como dict.get)."""
        valor = getattr(self, nombre)
        return defecto if valor is FALTA else valor

    def actualizar(self, datos=None, **extra):
        """Asigna varios campos a la vez (como dict.update)."""
        for nombre, valor in {**(datos or {}), **extra}.items():
            setattr(self, nombre, valor)

    def a_dict(self):
        """Diccionario con los campos asignados, en el orden en que se asignaron.

        Tiene las mismas claves que el diccionario que devolvía procesar_imagen
        en el notebook, así el demo y el evaluador lo usan igual.
        """
        return {nombre: getattr(self, nombre) for nombre in self._orden}


@dataclass
class Intento:
    """Lo que va produciendo intentar_resolver, paso a paso.

    Si un paso falla, los campos de los pasos anteriores quedan llenos y
    `etapa` dice en qué paso se estaba.
    """

    etapa: str = "ocr"
    pistas: Any = None
    fin_ocr: Any = None
    grupos: Any = None
    solucion: Any = None
    sumas: Any = None
    estadisticas: Any = None


def intentar_resolver(recortes, blancas, reforzado, intento):
    """Lee las pistas, arma los grupos y resuelve: la secuencia de cada intento.

    Recibe los recortes de las celdas, el set de blancas, si es la lectura
    reforzada (tras el filtro de bandas) y un Intento vacío que se va llenando.
    Devuelve el mismo Intento. Si algún paso lanza error, el error sale tal
    cual y el Intento conserva lo que se alcanzó a hacer.
    """
    intento.etapa = "ocr"
    intento.pistas = extraer_pistas(recortes, blancas, reforzado)
    intento.fin_ocr = perf_counter()
    intento.etapa = "grupos"
    intento.grupos = construir_grupos(blancas, intento.pistas)
    intento.etapa = "solver"
    intento.solucion, intento.sumas, intento.estadisticas = resolver_csp(blancas, intento.grupos)
    return intento


def _guardar_primer_intento(resultado, intento, blancas, inicio):
    """Copia al Resultado lo que alcanzó a hacer el primer intento."""
    if intento.pistas is not None:
        resultado.actualizar(
            blancas=blancas, pistas=intento.pistas, vision_ok=True, tiempo_vision_s=intento.fin_ocr - inicio
        )
    if intento.grupos is not None:
        resultado.grupos = intento.grupos
    if intento.estadisticas is not None:
        resultado.actualizar(
            intento.estadisticas,
            solucion=intento.solucion,
            sumas=intento.sumas,
            busquedas_cp=int(intento.estadisticas.get("tiempo_solver_s") is not None),
        )


def _combinar_reintento(resultado, extra, filtrada):
    """Suma al Resultado las estadísticas del reintento y, si resolvió, usa su solución."""
    stats_extra = extra.estadisticas
    resultado.actualizar(
        reintento_bandas=True,
        estado_inicial=resultado.estado,
        estado_reintento=stats_extra["estado"],
    )
    resultado.busquedas_cp += int(stats_extra.get("tiempo_solver_s") is not None)
    # Sumamos los tiempos de los intentos realizados.
    for clave in ("tiempo_modelo_s", "ramas", "conflictos"):
        setattr(resultado, clave, (resultado.obtener(clave) or 0) + (stats_extra.get(clave) or 0))
    tiempos = [
        t
        for t in (resultado.obtener("tiempo_solver_s"), stats_extra.get("tiempo_solver_s"))
        if t is not None
    ]
    resultado.tiempo_solver_s = sum(tiempos) if tiempos else None
    if extra.solucion is not None:
        resultado.actualizar(
            estado=stats_extra["estado"],
            solucion=extra.solucion,
            sumas=extra.sumas,
            grupos=extra.grupos,
            pistas=extra.pistas,
            imagen=filtrada,
            penalizacion=stats_extra.get("penalizacion"),
        )


def procesar_imagen(imagen):
    """Corre el pipeline completo sobre una imagen ya cargada.

    1. tablero: rectificar_tablero (perspectiva, n y líneas).
    2. clasificacion: segmentar_y_clasificar (celdas blancas).
    3. Primer intento: leer pistas -> grupos -> resolver.
    4. relectura: si no hubo solución, filtrar bandas y repetir el intento
       con la lectura reforzada.
    5. Si hay solución, listar las pistas ajustadas por el solver.

    Recibe la imagen BGR (o None si no se pudo leer).
    Devuelve un Resultado. No lanza errores: cualquier excepción queda en
    `error` y `error_etapa`.
    """
    inicio = perf_counter()
    resultado = Resultado()
    etapa = "tablero"
    try:
        if imagen is None:
            raise ValueError("No se pudo leer la imagen.")
        rectificada, n, lx, ly, puntaje = rectificar_tablero(imagen)
        resultado.actualizar(imagen=rectificada, n=n, lx=lx, ly=ly, puntaje_cuadricula=puntaje)
        etapa = "clasificacion"
        blancas, recortes = segmentar_y_clasificar(rectificada, n, lx, ly)

        primero = Intento()
        try:
            intentar_resolver(recortes, blancas, False, primero)
        finally:
            etapa = primero.etapa
            _guardar_primer_intento(resultado, primero, blancas, inicio)
        grupos, solucion, sumas = primero.grupos, primero.solucion, primero.sumas

        if solucion is None:
            etapa = "relectura"
            inicio_extra = perf_counter()
            filtrada = filtrar_bandas(rectificada, n)
            extra = Intento()
            try:
                intentar_resolver(recortar_celdas(filtrada, n, lx, ly), blancas, True, extra)
            finally:
                if extra.pistas is not None:
                    resultado.tiempo_vision_s += extra.fin_ocr - inicio_extra
            _combinar_reintento(resultado, extra, filtrada)
            if extra.solucion is not None:
                grupos, solucion, sumas = extra.grupos, extra.solucion, extra.sumas

        if solucion is not None:
            resultado.ajustes = [
                (g["origen"], g["direccion"], g["ocr"], s)
                for g, s in zip(grupos, sumas)
                if s != g["ocr"][0]
            ]
    except Exception as error:
        resultado.actualizar(error=str(error), error_etapa=etapa)
    if not resultado.tiene("tiempo_vision_s"):
        resultado.tiempo_vision_s = perf_counter() - inicio
    resultado.tiempo_total_s = perf_counter() - inicio
    return resultado


def leer_imagen(ruta):
    """Lee una imagen del disco en BGR.

    Usa np.fromfile + cv2.imdecode para aceptar rutas con tildes en Windows.
    Recibe la ruta. Devuelve la imagen, o None si el archivo no es una imagen
    válida (procesar_imagen lo reporta como error de la etapa "tablero").
    Lanza FileNotFoundError si el archivo no existe.
    """
    return cv2.imdecode(np.fromfile(str(ruta), dtype=np.uint8), cv2.IMREAD_COLOR)


def resolver_imagen(ruta):
    """Lee la imagen de `ruta` y la procesa. Devuelve un Resultado."""
    return procesar_imagen(leer_imagen(ruta))


def main(argumentos=None):
    """CLI: resuelve una imagen, imprime el resumen y guarda la imagen resuelta.

    Con --json también guarda el estado inicial leído (estructura.exportar_json).
    Devuelve 0 si hubo solución y 1 si no.
    """
    parser = argparse.ArgumentParser(description="Resuelve un Kakuro a partir de una imagen.")
    parser.add_argument("ruta", help="imagen del Kakuro (.png o .jpg)")
    parser.add_argument("--salida", default="kakuro_resuelto.png", help="dónde guardar la imagen resuelta")
    parser.add_argument("--json", help="dónde guardar el estado inicial leído (formato de data/ground_truth/)")
    args = parser.parse_args(argumentos)

    resultado = resolver_imagen(args.ruta)
    print("Estado del modelo:", resultado.estado)
    print(f"Tiempo total: {resultado.tiempo_total_s:.3f} s")
    if resultado.obtener("tiempo_solver_s") is not None:
        print(f"Tiempo del solver: {resultado.tiempo_solver_s:.4f} s")
    if resultado.obtener("reintento_bandas"):
        print("Se aplicó un filtro de bandas y se volvieron a leer las pistas.")
    if resultado.obtener("error"):
        print(f"Problema ({resultado.error_etapa}):", resultado.error)
    if resultado.obtener("ajustes"):
        print("Pistas ajustadas (celda, dirección, lectura -> suma usada):")
        for celda, direccion, candidatos, suma in resultado.ajustes:
            print(f"{celda}, {direccion}: {candidatos[0]} -> {suma}")
    if resultado.estado in {"PISTAS_SIN_LECTURA", "PISTAS_FUERA_DE_RANGO"}:
        print("No se leyeron bien algunas pistas. Prueba con una imagen más clara.")
    elif resultado.estado == "INFEASIBLE":
        print("Las pistas leídas no permiten una solución con las reglas de Kakuro.")

    if args.json:
        try:
            exportar_json(resultado, args.json, nombre_imagen=Path(args.ruta).name)
            print(f"Estado inicial guardado como: {args.json}")
        except ValueError as error:
            print("No se exportó el JSON:", error)

    if resultado.solucion is None:
        return 1
    cv2.imwrite(args.salida, dibujar_solucion(resultado.a_dict()))
    print(f"Imagen guardada como: {args.salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
