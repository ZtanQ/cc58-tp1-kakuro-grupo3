"""Verifica que los JSON de data/ground_truth/ sean Kakuros válidos.

Para cada JSON completo (imagen digital) revisa:
  - coordenadas dentro de 1..n, sin celdas blancas en la fila 1 ni en la columna 1;
  - que la solución cubra exactamente las celdas blancas;
  - que cada grupo tenga al menos 2 celdas, sume su pista y no repita dígitos;
  - cobertura: cada celda blanca está en exactamente un grupo horizontal y uno vertical;
  - unicidad: CP-SAT no encuentra otra solución distinta de la del JSON.
Para cada JSON de foto (con "base") revisa que la base exista, sea un JSON
completo y que la imagen de la foto exista en original/.

Uso:
    python scripts/verificar_ground_truth.py --datos data
Termina con código 1 si algún JSON tiene errores.
"""

import argparse
import json
import sys
from pathlib import Path

from ortools.sat.python import cp_model

DIGITO_MIN, DIGITO_MAX = 1, 9
LONGITUD_MINIMA_GRUPO = 2


def grupos_del_tablero(datos):
    """Arma los grupos (sumas) de un JSON completo.

    Recibe el contenido del JSON. Devuelve (blancas, grupos): el set de
    celdas blancas y una lista de tuplas (origen, direccion, suma, celdas).
    """
    blancas = {tuple(celda) for celda in datos["celdas_blancas"]}
    grupos = []
    for pista in datos["pistas"]:
        fila, columna = pista["origen"]
        for direccion, (df, dc) in (("derecha", (0, 1)), ("abajo", (1, 0))):
            if pista[direccion] is None:
                continue
            celdas, f, c = [], fila + df, columna + dc
            while (f, c) in blancas:
                celdas.append((f, c))
                f += df
                c += dc
            grupos.append(((fila, columna), direccion, pista[direccion], celdas))
    return blancas, grupos


def tiene_otra_solucion(blancas, grupos, solucion):
    """True si CP-SAT encuentra una solución distinta de `solucion`.

    Recibe las celdas blancas, los grupos y la solución {(fila, columna): dígito}.
    """
    modelo = cp_model.CpModel()
    x = {c: modelo.NewIntVar(DIGITO_MIN, DIGITO_MAX, f"x_{c[0]}_{c[1]}") for c in blancas}
    for _, _, suma, celdas in grupos:
        modelo.Add(sum(x[c] for c in celdas) == suma)
        modelo.AddAllDifferent([x[c] for c in celdas])
    distintas = []
    for celda in sorted(blancas):
        b = modelo.NewBoolVar(f"d_{celda[0]}_{celda[1]}")
        modelo.Add(x[celda] != solucion[celda]).OnlyEnforceIf(b)
        modelo.Add(x[celda] == solucion[celda]).OnlyEnforceIf(b.Not())
        distintas.append(b)
    modelo.AddBoolOr(distintas)
    return cp_model.CpSolver().Solve(modelo) in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def validar_tablero(datos):
    """Revisa un JSON completo (con celdas, pistas y solución).

    Recibe el contenido del JSON. Devuelve una lista de mensajes de error
    (vacía si el tablero es válido y tiene solución única).
    """
    n = datos["n"]
    errores = []
    blancas, grupos = grupos_del_tablero(datos)
    solucion = {tuple(int(x) for x in k.split(",")): v for k, v in datos["solucion"].items()}
    usadas = blancas | {tuple(p["origen"]) for p in datos["pistas"]}
    if any(not (1 <= f <= n and 1 <= c <= n) for f, c in usadas):
        errores.append("hay coordenadas fuera de 1..n")
    if any(f == 1 or c == 1 for f, c in blancas):
        errores.append("hay una celda blanca en la fila 1 o en la columna 1")
    if set(solucion) != blancas:
        errores.append("la solución no cubre exactamente las celdas blancas")
    for origen, direccion, suma, celdas in grupos:
        valores = [solucion.get(c) for c in celdas]
        if len(celdas) < LONGITUD_MINIMA_GRUPO:
            errores.append(f"grupo {origen} {direccion} con menos de {LONGITUD_MINIMA_GRUPO} celdas")
        if sum(v or 0 for v in valores) != suma:
            errores.append(f"grupo {origen} {direccion}: {valores} no suma {suma}")
        if len(set(valores)) != len(valores):
            errores.append(f"grupo {origen} {direccion}: dígitos repetidos {valores}")
    for celda in sorted(blancas):
        for direccion in ("derecha", "abajo"):
            veces = sum(1 for _, d, _, celdas in grupos if d == direccion and celda in celdas)
            if veces != 1:
                errores.append(f"celda {celda} está en {veces} grupos de dirección {direccion}")
    if not errores and tiene_otra_solucion(blancas, grupos, solucion):
        errores.append("tiene más de una solución")
    return errores


def verificar_carpeta(datos):
    """Verifica todos los JSON de <datos>/ground_truth/.

    Recibe la carpeta de datos (con original/ y ground_truth/). Devuelve un
    diccionario {nombre del JSON: lista de errores}.
    """
    datos = Path(datos)
    resultado = {}
    for ruta in sorted((datos / "ground_truth").glob("*.json")):
        contenido = json.loads(ruta.read_text(encoding="utf-8"))
        errores = []
        if not (datos / "original" / contenido.get("imagen", "")).is_file():
            errores.append(f"\"imagen\" = {contenido.get('imagen')} no existe en original/")
        elif Path(contenido["imagen"]).stem != ruta.stem:
            errores.append(f"\"imagen\" = {contenido['imagen']} no coincide con el nombre del JSON")
        if "base" in contenido:
            ruta_base = datos / "ground_truth" / f"{contenido['base']}.json"
            if not ruta_base.exists():
                errores.append(f"no existe el JSON base {ruta_base.name}")
            elif "base" in json.loads(ruta_base.read_text(encoding="utf-8")):
                errores.append(f"su base {ruta_base.name} también tiene \"base\"")
        else:
            errores.extend(validar_tablero(contenido))
        resultado[ruta.name] = errores
    return resultado


def main(argumentos=None):
    """Imprime el resultado de cada JSON y devuelve 1 si alguno tiene errores."""
    parser = argparse.ArgumentParser(description="Verifica los JSON del ground truth.")
    parser.add_argument("--datos", default="data", help="carpeta con original/ y ground_truth/")
    args = parser.parse_args(argumentos)
    resultado = verificar_carpeta(args.datos)
    for nombre, errores in resultado.items():
        print(("OK  " if not errores else "MAL ") + nombre + ("" if not errores else ": " + "; ".join(errores)))
    malos = sum(bool(e) for e in resultado.values())
    print(f"\n{len(resultado) - malos}/{len(resultado)} JSON válidos")
    return 1 if malos else 0


if __name__ == "__main__":
    sys.exit(main())
