"""Evalúa el pipeline sobre todo el dataset y lo compara con el ground truth.

Para cada imagen de <datos>/original/ carga <datos>/ground_truth/<mismo nombre>.json,
corre kakuro.pipeline.resolver_imagen y guarda:
  - <salida>/metricas.csv con una fila por imagen;
  - <salida>/rechazo.csv con las imágenes que el sistema debe rechazar;
  - <salida>/soluciones/<nombre>.png con la solución dibujada (si hubo solución);
  - <salida>/json/<nombre>.json con el estado inicial exportado
    (estructura.exportar_json), y la columna json_ok que dice si coincide con
    el ground truth en celdas blancas y pistas;
  - un resumen en consola comparable con la tabla de resultados del README.

Todo se cuenta contra el JSON, sin excepciones. Las fotos llevan un JSON
mínimo con "base" y se comparan contra el JSON de esa base. Las imágenes se
agrupan por tipo: digital, foto_papel y foto_pantalla. Las de
<datos>/rechazo/ se evalúan aparte: el acierto es no presentar solución.

Uso:
    python scripts/evaluar.py --datos data --salida resultados/
    python scripts/evaluar.py --rechazo ruta/a/foto.jpg   # rechazo extra
"""

import argparse
import csv
import json
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kakuro.estructura import exportar_json  # noqa: E402
from kakuro.pipeline import resolver_imagen  # noqa: E402
from kakuro.visualizacion import dibujar_solucion  # noqa: E402

EXTENSIONES = {".png", ".jpg", ".jpeg"}

TIPOS = ["digital", "foto_papel", "foto_pantalla"]

COLUMNAS = [
    "imagen", "tipo", "base", "condicion", "n_real", "n_detectado", "grilla_ok", "celdas_blancas_ok",
    "ocr_correctas", "ocr_total", "json_ok", "estado", "resuelto", "solucion_correcta",
    "celdas_correctas", "celdas_total", "incorrecta_presentada_como_correcta",
    "reintento_bandas", "n_ajustes", "ajustes", "n_pistas_sin_lectura",
    "error_etapa", "error", "puntaje_cuadricula", "ramas", "conflictos",
    "tiempo_total_s", "tiempo_vision_s", "tiempo_solver_s",
]

COLUMNAS_RECHAZO = ["imagen", "rechazada", "estado", "error_etapa", "error", "tiempo_total_s"]


def leer_json(ruta):
    """Lee un archivo JSON en UTF-8 y devuelve su contenido."""
    with open(ruta, encoding="utf-8") as archivo:
        return json.load(archivo)


def validar_bases(datos):
    """Revisa que todo JSON con "base" apunte a un original existente.

    Una foto lleva un JSON mínimo {"imagen", "base", "fuente"}; "base" es el
    nombre (sin extensión) de la imagen digital que se fotografió. Se exige:
      - que exista <datos>/original/<base>.png;
      - que exista <datos>/ground_truth/<base>.json y sea completo (sin "base",
        es decir, no se encadenan bases);
      - que "imagen" coincida con el nombre de la foto.

    Recibe la carpeta de datos. Devuelve una lista de mensajes de error
    (vacía si todo está bien).
    """
    errores = []
    for ruta in sorted((datos / "ground_truth").glob("*.json")):
        contenido = leer_json(ruta)
        if "base" not in contenido:
            continue
        base = contenido["base"]
        if not (datos / "original" / f"{base}.png").exists():
            errores.append(f"{ruta.name}: no existe la imagen base original/{base}.png")
        ruta_base = datos / "ground_truth" / f"{base}.json"
        if not ruta_base.exists():
            errores.append(f"{ruta.name}: no existe el JSON base {ruta_base.name}")
        elif "base" in leer_json(ruta_base):
            errores.append(f"{ruta.name}: su base {ruta_base.name} también tiene \"base\"")
        if not (datos / "original" / contenido["imagen"]).exists():
            errores.append(f"{ruta.name}: \"imagen\" = {contenido['imagen']} no existe en original/")
    return errores


def cargar_ground_truth(ruta_json):
    """Lee un JSON de ground truth y lo pasa a estructuras fáciles de comparar.

    Si el JSON tiene "base" (es una foto), las celdas, pistas y solución se
    toman del JSON de esa base, en la misma carpeta.

    Devuelve un diccionario con:
      - "n": tamaño de la grilla;
      - "blancas": set de (fila, columna);
      - "pistas": {(fila, columna, direccion): suma}, sin los null;
      - "solucion": {(fila, columna): dígito};
      - "base": nombre de la imagen base, o None si es una imagen digital.
    """
    ruta_json = Path(ruta_json)
    datos = leer_json(ruta_json)
    base = datos.get("base")
    if base is not None:
        datos = leer_json(ruta_json.parent / f"{base}.json")
    pistas = {}
    for pista in datos["pistas"]:
        fila, columna = pista["origen"]
        for direccion in ("derecha", "abajo"):
            if pista[direccion] is not None:
                pistas[(fila, columna, direccion)] = pista[direccion]
    solucion = {}
    for clave, valor in datos["solucion"].items():
        fila, columna = (int(parte) for parte in clave.split(","))
        solucion[(fila, columna)] = valor
    return {
        "n": datos["n"],
        "blancas": {tuple(celda) for celda in datos["celdas_blancas"]},
        "pistas": pistas,
        "solucion": solucion,
        "base": base,
    }


def clasificar(nombre, base):
    """Devuelve (tipo, condicion) de una imagen según su nombre.

    - Sin base: ("digital", "").
    - Con base: el nombre es {base}_{soporte}_{condicion}; el tipo es
      "foto_" + soporte (foto_papel o foto_pantalla).
    """
    if base is None:
        return "digital", ""
    resto = Path(nombre).stem[len(base) + 1:]
    soporte, _, condicion = resto.partition("_")
    return f"foto_{soporte}", condicion


def contar_ocr_correctas(pistas_leidas, pistas_reales):
    """Cuenta las pistas reales cuyo primer candidato del OCR es el valor correcto.

    Recibe las pistas leídas {(fila, columna): {"derecha": [...], "abajo": [...]}}
    (o None si no se llegó al OCR) y las reales {(fila, columna, direccion): suma}.
    Devuelve (correctas, total). Una pista no leída cuenta como incorrecta.
    """
    pistas_leidas = pistas_leidas or {}
    correctas = 0
    for (fila, columna, direccion), suma in pistas_reales.items():
        candidatos = pistas_leidas.get((fila, columna), {}).get(direccion, [])
        if candidatos and candidatos[0] == suma:
            correctas += 1
    return correctas, len(pistas_reales)


def comparar_json(exportado, gt):
    """Compara el estado inicial exportado con el ground truth.

    Coincide si las celdas blancas son las mismas, las pistas (solo las que no
    son null) son las mismas y no quedó ninguna pista sin lectura.
    Recibe la salida de estructura.exportar_json y la de cargar_ground_truth.
    Devuelve True o False.
    """
    blancas = {tuple(celda) for celda in exportado["celdas_blancas"]}
    pistas = {}
    for pista in exportado["pistas"]:
        fila, columna = pista["origen"]
        for direccion in ("derecha", "abajo"):
            if pista[direccion] is not None:
                pistas[(fila, columna, direccion)] = pista[direccion]
    return blancas == gt["blancas"] and pistas == gt["pistas"] and not exportado["pistas_sin_lectura"]


def _redondear(valor, decimales):
    """Redondea si es número; deja "" si es None."""
    return "" if valor is None else round(valor, decimales)


def evaluar_imagen(ruta_imagen, gt, carpeta_soluciones, carpeta_json):
    """Corre el pipeline sobre una imagen y calcula sus métricas.

    Recibe la ruta, su ground truth (salida de cargar_ground_truth), la
    carpeta donde guardar la imagen resuelta y la carpeta donde guardar el
    estado inicial exportado. Devuelve un diccionario con una entrada por
    cada nombre de COLUMNAS. json_ok queda vacío si la imagen no llegó a
    leer las pistas (no hay estado inicial que exportar).
    """
    r = resolver_imagen(ruta_imagen).a_dict()
    try:
        exportado = exportar_json(
            r, carpeta_json / (Path(ruta_imagen).stem + ".json"), nombre_imagen=Path(ruta_imagen).name
        )
        json_ok = comparar_json(exportado, gt)
    except ValueError:
        json_ok = ""
    tipo, condicion = clasificar(ruta_imagen, gt["base"])
    solucion = r.get("solucion")
    ocr_correctas, ocr_total = contar_ocr_correctas(r.get("pistas"), gt["pistas"])
    solucion_correcta = solucion == gt["solucion"]
    celdas_correctas = sum(1 for celda, v in gt["solucion"].items() if (solucion or {}).get(celda) == v)
    if solucion is not None:
        cv2.imwrite(str(carpeta_soluciones / (Path(ruta_imagen).stem + ".png")), dibujar_solucion(r))
    ajustes = r.get("ajustes") or []
    sin_lectura = sum(1 for lecturas in (r.get("pistas") or {}).values() for c in lecturas.values() if not c)
    return {
        "imagen": Path(ruta_imagen).name,
        "tipo": tipo,
        "base": gt["base"] or "",
        "condicion": condicion,
        "n_real": gt["n"],
        "n_detectado": r.get("n", ""),
        "grilla_ok": r.get("n") == gt["n"],
        "celdas_blancas_ok": r.get("blancas") == gt["blancas"],
        "ocr_correctas": ocr_correctas,
        "ocr_total": ocr_total,
        "json_ok": json_ok,
        "estado": r["estado"],
        "resuelto": solucion is not None,
        "solucion_correcta": solucion_correcta,
        "celdas_correctas": celdas_correctas,
        "celdas_total": len(gt["solucion"]),
        "incorrecta_presentada_como_correcta": solucion is not None and not solucion_correcta,
        "reintento_bandas": bool(r.get("reintento_bandas")),
        "n_ajustes": len(ajustes),
        "ajustes": "; ".join(f"{o[0]},{o[1]} {d}: {c[0]}->{s}" for o, d, c, s in ajustes),
        "n_pistas_sin_lectura": sin_lectura,
        "error_etapa": r.get("error_etapa", ""),
        "error": r.get("error", ""),
        "puntaje_cuadricula": _redondear(r.get("puntaje_cuadricula"), 3),
        "ramas": r.get("ramas", ""),
        "conflictos": r.get("conflictos", ""),
        "tiempo_total_s": _redondear(r["tiempo_total_s"], 3),
        "tiempo_vision_s": _redondear(r["tiempo_vision_s"], 3),
        "tiempo_solver_s": _redondear(r.get("tiempo_solver_s"), 4),
    }


def evaluar_rechazo(ruta_imagen):
    """Corre el pipeline sobre una imagen que debe rechazarse.

    Es un acierto si el sistema no presenta ninguna solución.
    Devuelve un diccionario con una entrada por cada nombre de COLUMNAS_RECHAZO.
    """
    r = resolver_imagen(ruta_imagen).a_dict()
    return {
        "imagen": Path(ruta_imagen).name,
        "rechazada": r.get("solucion") is None,
        "estado": r["estado"],
        "error_etapa": r.get("error_etapa", ""),
        "error": r.get("error", ""),
        "tiempo_total_s": round(r["tiempo_total_s"], 3),
    }


def listar_imagenes(ruta):
    """Lista las imágenes de una carpeta (ordenadas), o la ruta misma si es un archivo."""
    ruta = Path(ruta)
    if ruta.is_file():
        return [ruta]
    if not ruta.is_dir():
        return []
    return sorted(p for p in ruta.iterdir() if p.suffix.lower() in EXTENSIONES)


def guardar_csv(ruta, columnas, filas):
    """Escribe una lista de diccionarios como CSV."""
    with open(ruta, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas)
        escritor.writeheader()
        escritor.writerows(filas)


def resumir(filas):
    """Calcula las métricas agregadas de un grupo de filas.

    Devuelve una lista de tuplas (nombre de la métrica, valor como texto).
    """
    total = len(filas)
    if not total:
        return []
    ocr_ok = sum(f["ocr_correctas"] for f in filas)
    ocr_tot = sum(f["ocr_total"] for f in filas)
    solver = [f["tiempo_solver_s"] for f in filas if f["tiempo_solver_s"] != ""]
    return [
        ("Imágenes", str(total)),
        ("Tamaño de grilla correcto", f"{sum(f['grilla_ok'] for f in filas)}/{total}"),
        ("Celdas blancas correctas", f"{sum(f['celdas_blancas_ok'] for f in filas)}/{total}"),
        ("OCR, pista correcta en primer candidato",
         f"{ocr_ok}/{ocr_tot} ({100 * ocr_ok / ocr_tot:.0f}%)" if ocr_tot else "-"),
        ("JSON exportado = ground truth", f"{sum(f['json_ok'] is True for f in filas)}/{total}"),
        ("Solución correcta", f"{sum(f['solucion_correcta'] for f in filas)}/{total}"),
        ("Incorrectas presentadas como correctas",
         str(sum(f["incorrecta_presentada_como_correcta"] for f in filas))),
        ("Sin solución (rechazadas)", str(sum(not f["resuelto"] for f in filas))),
        ("Usaron el reintento de bandas", str(sum(f["reintento_bandas"] for f in filas))),
        ("Pistas ajustadas por el solver", str(sum(f["n_ajustes"] for f in filas))),
        ("Tiempo promedio por imagen", f"{sum(f['tiempo_total_s'] for f in filas) / total:.2f} s"),
        ("Tiempo de visión promedio", f"{sum(f['tiempo_vision_s'] for f in filas) / total:.2f} s"),
        ("Tiempo del solver", f"{1000 * min(solver):.0f}–{1000 * max(solver):.0f} ms" if solver else "-"),
    ]


def imprimir_resumen(filas, rechazos):
    """Imprime una tabla con las métricas por tipo de imagen y en total, y los rechazos."""
    grupos = [(tipo, [f for f in filas if f["tipo"] == tipo]) for tipo in TIPOS]
    grupos = [(tipo, g) for tipo, g in grupos if g] + [("total", filas)]
    resumenes = [dict(resumir(g)) for _, g in grupos]
    nombres = [nombre for nombre, _ in resumir(filas)]
    ancho = max(len(n) for n in nombres) + 2
    columna = max(16, max(len(v) for r in resumenes for v in r.values()) + 2)
    linea = "=" * (ancho + columna * len(grupos))
    print()
    print(linea)
    print(f"{'Métrica':<{ancho}}" + "".join(f"{tipo:>{columna}}" for tipo, _ in grupos))
    print("-" * len(linea))
    for nombre in nombres:
        print(f"{nombre:<{ancho}}" + "".join(f"{r.get(nombre, '-'):>{columna}}" for r in resumenes))
    print(linea)
    if rechazos:
        print(f"{'Rechazos correctos (data/rechazo)':<{ancho}}"
              f"{sum(f['rechazada'] for f in rechazos)}/{len(rechazos)}")


def main(argumentos=None):
    """Recorre el dataset y las imágenes de rechazo, y guarda los CSV."""
    parser = argparse.ArgumentParser(description="Evalúa el pipeline contra el ground truth.")
    parser.add_argument("--datos", default="data", help="carpeta con original/ y ground_truth/")
    parser.add_argument("--salida", default="resultados", help="carpeta donde guardar métricas e imágenes")
    parser.add_argument("--rechazo", nargs="*", default=None,
                        help="carpetas o imágenes que deben rechazarse (por defecto <datos>/rechazo)")
    args = parser.parse_args(argumentos)

    datos, salida = Path(args.datos), Path(args.salida)
    errores = validar_bases(datos)
    if errores:
        print("JSON con \"base\" inválido:")
        for error in errores:
            print("  -", error)
        return 1
    carpeta_soluciones = salida / "soluciones"
    carpeta_soluciones.mkdir(parents=True, exist_ok=True)
    carpeta_json = salida / "json"
    carpeta_json.mkdir(parents=True, exist_ok=True)

    filas = []
    for ruta in listar_imagenes(datos / "original"):
        ruta_json = datos / "ground_truth" / (ruta.stem + ".json")
        if not ruta_json.exists():
            print(f"[omitida] {ruta.name}: no existe {ruta_json.name}")
            continue
        fila = evaluar_imagen(ruta, cargar_ground_truth(ruta_json), carpeta_soluciones, carpeta_json)
        filas.append(fila)
        marca = "OK " if fila["solucion_correcta"] else ("MAL" if fila["resuelto"] else "---")
        detalle = f"  [{fila['error_etapa']}] {fila['error']}" if fila["error"] else ""
        extra = " reintento" if fila["reintento_bandas"] else ""
        print(f"{marca} {ruta.name:<52} n={fila['n_detectado'] or '?'}/{fila['n_real']} "
              f"ocr={fila['ocr_correctas']}/{fila['ocr_total']:<3} "
              f"celdas={fila['celdas_correctas']}/{fila['celdas_total']:<3} {fila['estado']:<18} "
              f"{fila['tiempo_total_s']:.1f}s{extra}{detalle}", flush=True)
    guardar_csv(salida / "metricas.csv", COLUMNAS, filas)

    rutas_rechazo = args.rechazo if args.rechazo is not None else [datos / "rechazo"]
    rechazos = []
    for ruta in (p for r in rutas_rechazo for p in listar_imagenes(r)):
        fila = evaluar_rechazo(ruta)
        rechazos.append(fila)
        marca = "OK " if fila["rechazada"] else "MAL"
        print(f"{marca} [rechazo] {ruta.name}: {fila['estado']} [{fila['error_etapa']}] {fila['error']}")
    if rechazos:
        guardar_csv(salida / "rechazo.csv", COLUMNAS_RECHAZO, rechazos)

    imprimir_resumen(filas, rechazos)
    print(f"Métricas guardadas en {salida / 'metricas.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
