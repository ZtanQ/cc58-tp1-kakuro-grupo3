import argparse
import csv
import json
import os
import random

from PIL import Image, ImageDraw, ImageFont
from ortools.sat.python import cp_model

# 1. GENERACIÓN DEL PUZZLE

def _hay_corridas_de_1(blanca, n):
    """Devuelve las celdas blancas que forman una corrida (horizontal o
    vertical) de longitud 1. En Kakuro toda corrida debe tener >= 2 celdas."""
    malas = set()
    for f in range(n):
        for c in range(n):
            if not blanca[f][c]:
                continue
            izq = c > 0 and blanca[f][c - 1]
            der = c < n - 1 and blanca[f][c + 1]
            arr = f > 0 and blanca[f - 1][c]
            aba = f < n - 1 and blanca[f + 1][c]
            if not (izq or der) or not (arr or aba):
                malas.add((f, c))
    return malas


def generar_mascara(n, rng, densidad_negras):
    """Crea la máscara blanca/negra del tablero (True = casilla blanca)."""
    blanca = [[False] * n for _ in range(n)]
    for f in range(1, n):
        for c in range(1, n):
            blanca[f][c] = rng.random() > densidad_negras
    # Limpia hasta que no queden corridas de longitud 1
    while True:
        malas = _hay_corridas_de_1(blanca, n)
        if not malas:
            break
        for f, c in malas:
            blanca[f][c] = False
    return blanca


def obtener_corridas(blanca, n):
    """Lista de corridas: dict(direccion, origen, celdas) con coords 0-index.
    'origen' es la celda de pista que la controla."""
    corridas = []
    for f in range(n):
        c = 0
        while c < n:
            if blanca[f][c]:
                ini = c
                while c < n and blanca[f][c]:
                    c += 1
                corridas.append({"direccion": "derecha", "origen": (f, ini - 1),
                                 "celdas": [(f, k) for k in range(ini, c)]})
            else:
                c += 1
    for c in range(n):
        f = 0
        while f < n:
            if blanca[f][c]:
                ini = f
                while f < n and blanca[f][c]:
                    f += 1
                corridas.append({"direccion": "abajo", "origen": (ini - 1, c),
                                 "celdas": [(k, c) for k in range(ini, f)]})
            else:
                f += 1
    return corridas


def llenar_solucion(blanca, n, corridas, rng, sesgo_extremos=False):
    """Llena las casillas blancas con dígitos 1-9 sin repetir en ninguna
    corrida (backtracking aleatorio). Con sesgo_extremos se prefieren dígitos
    muy bajos o muy altos: producen sumas con pocas combinaciones posibles y
    por eso favorecen que el puzzle tenga solución única."""
    celdas = [(f, c) for f in range(n) for c in range(n) if blanca[f][c]]
    corridas_de = {celda: [] for celda in celdas}
    for i, corr in enumerate(corridas):
        for celda in corr["celdas"]:
            corridas_de[celda].append(i)
    valores = {}

    def usados(celda):
        s = set()
        for i in corridas_de[celda]:
            for otra in corridas[i]["celdas"]:
                if otra in valores:
                    s.add(valores[otra])
        return s

    def bt(k):
        if k == len(celdas):
            return True
        celda = celdas[k]
        opciones = [d for d in range(1, 10) if d not in usados(celda)]
        if sesgo_extremos:
            opciones.sort(key=lambda d: -abs(d - 5) + rng.random() * 3)
        else:
            rng.shuffle(opciones)
        for d in opciones:
            valores[celda] = d
            if bt(k + 1):
                return True
            del valores[celda]
        return False

    return valores if bt(0) else None


def buscar_alternativa(blanca, n, corridas, solucion):
    """Con CP-SAT busca una solución DISTINTA a la original.
    Devuelve None si la solución es única; si no, devuelve la alternativa."""
    modelo = cp_model.CpModel()
    var = {(f, c): modelo.NewIntVar(1, 9, f"x{f}_{c}")
           for f in range(n) for c in range(n) if blanca[f][c]}
    for corr in corridas:
        vs = [var[c] for c in corr["celdas"]]
        modelo.AddAllDifferent(vs)
        modelo.Add(sum(vs) == corr["suma"])
    # obliga a que al menos una casilla sea distinta a la solución original
    difs = []
    for celda, v in solucion.items():
        b = modelo.NewBoolVar(f"d{celda[0]}_{celda[1]}")
        modelo.Add(var[celda] != v).OnlyEnforceIf(b)
        modelo.Add(var[celda] == v).OnlyEnforceIf(b.Not())
        difs.append(b)
    modelo.AddBoolOr(difs)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10
    estado = solver.Solve(modelo)
    if estado in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {celda: solver.Value(v) for celda, v in var.items()}
    return None


def _limpiar(blanca, n):
    """Quita casillas hasta que no queden corridas de longitud 1."""
    while True:
        malas = _hay_corridas_de_1(blanca, n)
        if not malas:
            return
        for f, c in malas:
            blanca[f][c] = False


def _armar(blanca, n, rng, sesgo=False):
    """Dada una máscara, calcula corridas, solución aleatoria y sumas."""
    corridas = obtener_corridas(blanca, n)
    if not corridas or any(len(c["celdas"]) > 9 for c in corridas):
        return None
    sol = llenar_solucion(blanca, n, corridas, rng, sesgo_extremos=sesgo)
    if sol is None:
        return None
    for corr in corridas:
        corr["suma"] = sum(sol[c] for c in corr["celdas"])
    return corridas, sol


def generar_kakuro(n, rng, max_intentos=60, permitir_multiples=False):
    """Genera un Kakuro n x n con solución única.

    Estrategia:
      1. Se crea una máscara blanca/negra al azar.
      2. Se prueban varias soluciones aleatorias para esa máscara (cada una da
         sumas distintas) y se verifica con CP-SAT si el puzzle es único.
      3. Si ninguna sirve, se REPARA la máscara: se pone en negro una casilla
         donde dos soluciones difieren y se vuelve al paso 2.
    """
    minimo_blancas = max(4, int(0.42 * (n - 1) ** 2))
    for intento in range(max_intentos):
        blanca = generar_mascara(n, rng, rng.uniform(0.08, 0.22) + 0.02 * (n - 4))
        for _ in range(25):  # pasos de reparación de la máscara
            if sum(sum(fila) for fila in blanca) < minimo_blancas:
                break
            ultima_alt = None
            for prueba in range(12):  # varias soluciones para la misma máscara
                armado = _armar(blanca, n, rng, sesgo=(prueba % 5 != 0))
                if armado is None:
                    break
                corridas, sol = armado
                alt = None if permitir_multiples else \
                    buscar_alternativa(blanca, n, corridas, sol)
                if alt is None:
                    return {"n": n, "blanca": blanca, "corridas": corridas,
                            "solucion": sol, "intentos": intento + 1}
                ultima_alt = (sol, alt)
            if ultima_alt is None:
                break
            sol, alt = ultima_alt
            dif = [c for c in sol if sol[c] != alt[c]]
            for c in rng.sample(dif, k=min(len(dif), 1)):
                blanca[c[0]][c[1]] = False
            _limpiar(blanca, n)
    raise RuntimeError(f"No se logró generar un Kakuro único de {n}x{n}. "
                       "Prueba otro tamaño/semilla o usa --permitir-multiples.")


# 2. DIBUJO DE LA IMAGEN


ESTILOS = {
    # negro con números blancos (el más común en apps/web)
    "clasico": {"celda_pista": (25, 25, 25), "texto_pista": (255, 255, 255),
                "diagonal": (255, 255, 255)},
    # gris claro con números negros (típico de periódico/libro impreso)
    "gris": {"celda_pista": (150, 150, 150), "texto_pista": (0, 0, 0),
             "diagonal": (0, 0, 0)},
}


def _fuente(tam, negrita=True):
    candidatos = [
        "DejaVuSans-Bold.ttf" if negrita else "DejaVuSans.ttf",
        "arialbd.ttf" if negrita else "arial.ttf",
        "Arial Bold.ttf" if negrita else "Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ]
    for nombre in candidatos:
        try:
            return ImageFont.truetype(nombre, tam)
        except OSError:
            continue
    return ImageFont.load_default(tam)


def dibujar_kakuro(puzzle, celda_px=110, margen=60, estilo="clasico",
                   solucion=False, separadores=True):
    """Dibuja el tablero. Si solucion=True escribe los dígitos en las casillas.
    separadores=True dibuja una línea gris clara entre celdas negras vecinas
    (como hacen muchos Kakuros reales). Con False esas líneas desaparecen
    (negro sobre negro), lo que hace mucho más difícil detectar la cuadrícula."""
    n, blanca = puzzle["n"], puzzle["blanca"]
    est = ESTILOS[estilo]
    lado = n * celda_px
    img = Image.new("RGB", (lado + 2 * margen, lado + 2 * margen), (255, 255, 255))
    d = ImageDraw.Draw(img)
    f_pista = _fuente(int(celda_px * 0.27))
    f_sol = _fuente(int(celda_px * 0.55), negrita=False)

    # Pistas por celda de origen
    pistas = {}
    for corr in puzzle["corridas"]:
        pistas.setdefault(corr["origen"], {})[corr["direccion"]] = corr["suma"]

    for f in range(n):
        for c in range(n):
            x1, y1 = margen + c * celda_px, margen + f * celda_px
            x2, y2 = x1 + celda_px, y1 + celda_px
            if blanca[f][c]:
                d.rectangle([x1, y1, x2, y2], fill=(255, 255, 255))
                if solucion:
                    v = str(puzzle["solucion"][(f, c)])
                    tw = d.textlength(v, font=f_sol)
                    d.text((x1 + (celda_px - tw) / 2, y1 + celda_px * 0.18), v,
                           font=f_sol, fill=(30, 30, 200))
            else:
                d.rectangle([x1, y1, x2, y2], fill=est["celda_pista"])
                p = pistas.get((f, c), {})
                if p:  # diagonal solo si la celda lleva pista
                    d.line([x1, y1, x2, y2], fill=est["diagonal"], width=3)
                if "derecha" in p:  # arriba-derecha
                    t = str(p["derecha"])
                    tw = d.textlength(t, font=f_pista)
                    d.text((x2 - tw - celda_px * 0.08, y1 + celda_px * 0.06), t,
                           font=f_pista, fill=est["texto_pista"])
                if "abajo" in p:  # abajo-izquierda
                    t = str(p["abajo"])
                    d.text((x1 + celda_px * 0.08, y2 - celda_px * 0.34), t,
                           font=f_pista, fill=est["texto_pista"])

    # Líneas de la cuadrícula, borde por borde de celda: negras si tocan una
    # casilla blanca; grises claras (o invisibles) entre celdas negras.
    color_sep = (135, 135, 135) if separadores else est["celda_pista"]
    for f in range(n):
        for c in range(n):
            x1, y1 = margen + c * celda_px, margen + f * celda_px
            x2, y2 = x1 + celda_px, y1 + celda_px
            # borde superior (compartido con la celda de arriba)
            arriba_blanca = f > 0 and blanca[f - 1][c]
            col = (0, 0, 0) if (blanca[f][c] or arriba_blanca) else color_sep
            d.line([x1, y1, x2, y1], fill=col, width=2)
            # borde izquierdo (compartido con la celda de la izquierda)
            izq_blanca = c > 0 and blanca[f][c - 1]
            col = (0, 0, 0) if (blanca[f][c] or izq_blanca) else color_sep
            d.line([x1, y1, x1, y2], fill=col, width=2)
    d.rectangle([margen, margen, margen + lado, margen + lado],
                outline=(0, 0, 0), width=8)
    return img



# 3. SALIDA: JSON, CSV, PDF


def guardar_json(puzzle, ruta, nombre_img, estilo):
    """Ground truth con coordenadas (fila, columna) desde 1."""
    n = puzzle["n"]
    pistas = {}
    for corr in puzzle["corridas"]:
        f, c = corr["origen"]
        clave = f"{f + 1},{c + 1}"
        pistas.setdefault(clave, {"origen": [f + 1, c + 1], "derecha": None, "abajo": None})
        pistas[clave][corr["direccion"]] = corr["suma"]
    datos = {
        "imagen": nombre_img,
        "n": n,
        "estilo": estilo,
        "celdas_blancas": [[f + 1, c + 1] for f in range(n) for c in range(n)
                           if puzzle["blanca"][f][c]],
        "pistas": list(pistas.values()),
        "solucion": {f"{f + 1},{c + 1}": v for (f, c), v in sorted(puzzle["solucion"].items())},
    }
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump(datos, fh, ensure_ascii=False, indent=2)


def guardar_pdf(rutas_png, ruta_pdf):
    """Une los tableros (sin solución) en un PDF A4, uno por página."""
    a4 = (1654, 2339)  # A4 a 200 dpi
    paginas = []
    for ruta in rutas_png:
        img = Image.open(ruta).convert("RGB")
        escala = min((a4[0] * 0.85) / img.width, (a4[1] * 0.6) / img.height)
        img = img.resize((int(img.width * escala), int(img.height * escala)), Image.LANCZOS)
        pag = Image.new("RGB", a4, (255, 255, 255))
        pag.paste(img, ((a4[0] - img.width) // 2, 220))
        d = ImageDraw.Draw(pag)
        d.text((100, 80), os.path.splitext(os.path.basename(ruta))[0],
               font=_fuente(42), fill=(90, 90, 90))
        paginas.append(pag)
    paginas[0].save(ruta_pdf, save_all=True, append_images=paginas[1:], resolution=200)



# 4. PROGRAMA PRINCIPAL


def main():
    ap = argparse.ArgumentParser(description="Generador de Kakuros para el dataset")
    ap.add_argument("--cantidad", type=int, default=8, help="cuántos puzzles generar")
    ap.add_argument("--tamanos", type=int, nargs="+", default=[4, 5, 6, 7],
                    help="tamaños n (3 a 7); se reparten en orden cíclico")
    ap.add_argument("--salida", default="data/generado", help="carpeta de salida")
    ap.add_argument("--semilla", type=int, default=42, help="semilla (reproducible)")
    ap.add_argument("--estilo", choices=list(ESTILOS), default="clasico",
                    help="clasico = negro/blanco, gris = gris/negro")
    ap.add_argument("--sin-separadores", action="store_true",
                    help="sin líneas claras entre celdas negras (más difícil para la visión)")
    ap.add_argument("--pdf", action="store_true", help="crea PDF para imprimir")
    ap.add_argument("--con-solucion", action="store_true",
                    help="guarda también la imagen con la solución escrita")
    ap.add_argument("--permitir-multiples", action="store_true",
                    help="no exige solución única (más rápido, menos recomendable)")
    args = ap.parse_args()

    for t in args.tamanos:
        if not 3 <= t <= 7:
            ap.error("el notebook solo admite tamaños de 3 a 7")

    rng = random.Random(args.semilla)
    carpetas = {k: os.path.join(args.salida, k)
                for k in ("imagenes", "ground_truth", "soluciones")}
    for k, ruta in carpetas.items():
        if k == "soluciones" and not args.con_solucion:
            continue
        os.makedirs(ruta, exist_ok=True)

    filas_csv, pngs = [], []
    for i in range(args.cantidad):
        n = args.tamanos[i % len(args.tamanos)]
        puzzle = None
        for reintento in range(5):  # los tableros grandes a veces tardan varios intentos
            try:
                puzzle = generar_kakuro(n, rng, permitir_multiples=args.permitir_multiples)
                break
            except RuntimeError:
                print(f"   ({n}x{n}: reintentando...)")
        if puzzle is None:
            print(f"[!] No se pudo generar el puzzle {i + 1} de {n}x{n}; se omite.")
            continue
        nombre = f"kakuro_{n:02d}x{n:02d}_{args.estilo}_{i + 1:02d}"
        img = dibujar_kakuro(puzzle, estilo=args.estilo,
                             separadores=not args.sin_separadores)
        ruta_png = os.path.join(carpetas["imagenes"], nombre + ".png")
        img.save(ruta_png)
        pngs.append(ruta_png)
        guardar_json(puzzle, os.path.join(carpetas["ground_truth"], nombre + ".json"),
                     nombre + ".png", args.estilo)
        if args.con_solucion:
            dibujar_kakuro(puzzle, estilo=args.estilo, solucion=True,
                           separadores=not args.sin_separadores).save(
                os.path.join(carpetas["soluciones"], nombre + "_solucion.png"))
        filas_csv.append([nombre + ".png", n, args.estilo, "digital", "limpia",
                          "frontal", "generado con script"])
        print(f"[ok] {nombre}  ({puzzle['intentos']} intentos)")

    with open(os.path.join(args.salida, "metadata.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["archivo", "n", "estilo", "tipo", "condicion", "detalle", "origen"])
        w.writerows(filas_csv)

    if args.pdf:
        ruta_pdf = os.path.join(args.salida, "kakuros_para_imprimir.pdf")
        guardar_pdf(pngs, ruta_pdf)
        print(f"[ok] PDF para imprimir: {ruta_pdf}")
    print(f"\nListo. Todo quedó en la carpeta '{args.salida}/'.")


if __name__ == "__main__":
    main()
