"""Genera resultados/resumen.md a partir de la salida de evaluar.py.

Lee <resultados>/metricas.csv y <resultados>/rechazo.csv y escribe
<resultados>/resumen.md con las tablas para el informe:
  1. resultados por tipo de imagen y rechazo;
  2. fotos por condición;
  3. tiempo, ramas y conflictos del solver por tamaño de tablero;
  4. imágenes que no se resuelven bien y su causa;
  5. pistas ajustadas por el solver;
  6. historial (notebook viejo -> Grupo3 -> actual).

Uso (después de correr evaluar.py):
    python scripts/generar_resumen.py --resultados resultados \\
        --condiciones "Tesseract 5.3.4, OpenCV 5.0.0, ... commit abc1234"
"""

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

TIPOS = [("digital", "Digital"), ("foto_papel", "Foto papel"), ("foto_pantalla", "Foto pantalla")]

# Causas analizadas a mano, imagen por imagen. Si aparece una falla nueva,
# su fila sale con la causa vacía y hay que analizarla.
CAUSAS = {
    "KC_kakuro_07x07_dificil_pantalla_muy_inclinada.jpg":
        "5 celdas blancas del extremo lejano salen como oscuras; los grupos quedan sin sumas posibles.",
    "L_kakuro_03x03_clasico_06_papel_sombra.jpg":
        "La sombra tapa el \"1\" de 15 y se lee 5. El solver demuestra que no hay solución: rechazo correcto, "
        "no inventa la pista.",
    "L_kakuro_07x07_clasico_01_papel_sombra.jpg":
        "La sombra mueve el umbral y 9 celdas oscuras pasan como blancas; aparece una \"pista\" sin número.",
    "L_kakuro_05x05_clasico_01_papel_borrosa.jpg":
        "309×307 px (~60 px por celda). Lee 16 en vez de 18, ajusta 3→5 y encuentra **otro Kakuro válido**: "
        "error silencioso.",
}

# Valores medidos antes de esta versión del código: notebook viejo y notebook
# Grupo3 con los JSON sin corregir, ambos sobre las 31 imágenes digitales.
HISTORIAL = [
    ("Tamaño de grilla correcto", "17/31", "29/31"),
    ("Celdas blancas correctas", "17/17", "29/31"),
    ("OCR, primer candidato", "70/119 (59%)", "251/261 (96%)"),
    ("Solución correcta", "6/31", "29/31"),
    ("Incorrectas presentadas como correctas", "8", "2"),
]


def es(fila, columna):
    """True si la columna del CSV vale "True"."""
    return fila[columna] == "True"


def fraccion(grupo, columna):
    """Texto "aciertos/total" de una columna booleana."""
    return f"{sum(es(f, columna) for f in grupo)}/{len(grupo)}"


def ocr(grupo):
    """Texto "correctas/total (porcentaje)" del OCR en primer candidato."""
    correctas = sum(int(f["ocr_correctas"]) for f in grupo)
    total = sum(int(f["ocr_total"]) for f in grupo)
    return f"{correctas}/{total} ({100 * correctas / total:.0f}%)"


def rango_solver(grupo):
    """Texto "mín–máx ms" del tiempo del solver (solo donde se llamó a CP-SAT)."""
    tiempos = [float(f["tiempo_solver_s"]) for f in grupo if f["tiempo_solver_s"]]
    return f"{1000 * min(tiempos):.0f}–{1000 * max(tiempos):.0f} ms" if tiempos else "-"


def promedio(grupo, columna):
    """Promedio en segundos de una columna numérica."""
    return f"{sum(float(f[columna]) for f in grupo) / len(grupo):.2f} s"


def es_ajuste_diagonal(ajuste):
    """True si un ajuste es "4x -> 1x": un "1" junto a la diagonal leído como "4"."""
    m = re.search(r": (\d+)->(\d+)$", ajuste)
    if not m:
        return False
    leida, usada = m.groups()
    return len(leida) == 2 and leida[0] == "4" and usada == "1" + leida[1]


METRICAS = [
    ("Imágenes", lambda g: str(len(g))),
    ("Tamaño de grilla correcto", lambda g: fraccion(g, "grilla_ok")),
    ("Celdas blancas correctas", lambda g: fraccion(g, "celdas_blancas_ok")),
    ("OCR, pista correcta en primer candidato", ocr),
    ("JSON exportado = ground truth", lambda g: fraccion(g, "json_ok")),
    ("**Solución correcta**", lambda g: f"**{fraccion(g, 'solucion_correcta')}**"),
    ("Incorrectas presentadas como correctas",
     lambda g: str(sum(es(f, "incorrecta_presentada_como_correcta") for f in g))),
    ("Sin solución (el sistema no inventa)", lambda g: str(sum(not es(f, "resuelto") for f in g))),
    ("Usaron el reintento de bandas", lambda g: str(sum(es(f, "reintento_bandas") for f in g))),
    ("Pistas ajustadas por el solver", lambda g: str(sum(int(f["n_ajustes"]) for f in g))),
    ("Tiempo promedio por imagen", lambda g: promedio(g, "tiempo_total_s")),
    ("Tiempo de visión promedio", lambda g: promedio(g, "tiempo_vision_s")),
    ("Tiempo del solver (mín–máx)", rango_solver),
]


def generar(filas, rechazos, condiciones):
    """Arma el texto Markdown del resumen.

    Recibe las filas de metricas.csv y de rechazo.csv (listas de diccionarios)
    y el texto con las condiciones de la medición. Devuelve el Markdown.
    """
    grupos = [(nombre, [f for f in filas if f["tipo"] == t]) for t, nombre in TIPOS]
    grupos = [(n, g) for n, g in grupos if g] + [("**Total**", filas)]
    o = ["# Resumen de métricas finales\n",
         "Tablas para el informe. Se generan a partir de `resultados/metricas.csv` y `resultados/rechazo.csv`, "
         "que produce:\n",
         "```bash\npython scripts/evaluar.py --datos data --salida resultados/\n```\n",
         f"Condiciones de la medición: {condiciones}. Todo se cuenta contra el JSON de `data/ground_truth/`; "
         "las fotos se comparan con el JSON de su imagen base.\n",
         "## 1. Resultados por tipo de imagen\n",
         "| Métrica | " + " | ".join(n for n, _ in grupos) + " |",
         "|---|" + "---|" * len(grupos)]
    for nombre, calcular in METRICAS:
        o.append(f"| {nombre} | " + " | ".join(calcular(g) for _, g in grupos) + " |")
    o.append(f"\n**Rechazo** (`data/rechazo/`, el acierto es no presentar solución): "
             f"{sum(es(f, 'rechazada') for f in rechazos)}/{len(rechazos)}.")
    for f in rechazos:
        o.append(f"- `{f['imagen']}`: estado `{f['estado']}`, etapa `{f['error_etapa']}`. Mensaje: \"{f['error']}\"")
    o.append("\nLos tiempos dependen de la máquina. En Colab, el equipo midió ~3.4 s por imagen digital. "
             "En todos los casos casi todo el tiempo es OCR.\n")

    o += ["## 2. Fotos por condición\n",
          "| Soporte | Condición | Fotos | Solución correcta | OCR primer candidato | Reintento |",
          "|---|---|---|---|---|---|"]
    por_condicion = defaultdict(list)
    for f in filas:
        if f["tipo"] != "digital":
            por_condicion[(f["tipo"].replace("foto_", ""), f["condicion"])].append(f)
    for (soporte, condicion), g in sorted(por_condicion.items()):
        o.append(f"| {soporte} | {condicion} | {len(g)} | {fraccion(g, 'solucion_correcta')} | {ocr(g)} | "
                 f"{sum(es(f, 'reintento_bandas') for f in g)} |")
    o.append("")

    o += ["## 3. Tiempo del solver por tamaño de tablero\n",
          "Solo las imágenes donde se llamó a CP-SAT. Ramas y conflictos son los que reporta CP-SAT "
          "(sumados si hubo reintento).\n",
          "| n | Imágenes | Tiempo mín | Tiempo prom | Tiempo máx | Ramas máx | Conflictos máx |",
          "|---|---|---|---|---|---|---|"]
    for n in sorted({f["n_real"] for f in filas}, key=int):
        g = [f for f in filas if f["n_real"] == n and f["tiempo_solver_s"]]
        if not g:
            continue
        t = [1000 * float(f["tiempo_solver_s"]) for f in g]
        o.append(f"| {n}×{n} | {len(g)} | {min(t):.1f} ms | {sum(t) / len(t):.1f} ms | {max(t):.1f} ms | "
                 f"{max(int(f['ramas']) for f in g)} | {max(int(f['conflictos']) for f in g)} |")
    o.append("")

    o += ["## 4. Fotos que no se resuelven bien\n",
          "| Imagen | Estado | Reintento | OCR | Celdas blancas | Causa |",
          "|---|---|---|---|---|---|"]
    for f in filas:
        if not es(f, "solucion_correcta"):
            o.append(f"| `{f['imagen']}` | `{f['estado']}` | {'sí' if es(f, 'reintento_bandas') else 'no'} | "
                     f"{f['ocr_correctas']}/{f['ocr_total']} | {'sí' if es(f, 'celdas_blancas_ok') else 'no'} | "
                     f"{CAUSAS.get(f['imagen'], '')} |")
    o.append("")

    o += ["## 5. Pistas ajustadas por el solver\n",
          "Una pista ajustada es una suma que el solver cambió respecto del primer candidato del OCR, usando la "
          "tabla de confusiones de dígitos.\n",
          "| Imagen | Ajustes | ¿Solución correcta? |",
          "|---|---|---|"]
    ajustes = []
    for f in filas:
        if int(f["n_ajustes"]):
            o.append(f"| `{f['imagen']}` | {f['ajustes']} | {'sí' if es(f, 'solucion_correcta') else '**no**'} |")
            ajustes += f["ajustes"].split("; ")
    diagonal = [a for a in ajustes if es_ajuste_diagonal(a)]
    if diagonal:
        ejemplos = ", ".join(dict.fromkeys(a.split(": ")[1].replace("->", "→") for a in diagonal))
        o.append(f"\n{len(diagonal)} de los {len(ajustes)} ajustes son un \"1\" junto a la diagonal leído como "
                 f"\"4\" ({ejemplos}). Se podría probar un "
                 f"`DESPLAZAMIENTO_DIAGONAL` mayor que 0.09 en `config.py` y medir de nuevo.\n")
    else:
        o.append("")

    digitales = grupos[0][1] if grupos[0][0] == "Digital" else []
    o += ["## 6. Historial\n",
          "| Métrica | Notebook viejo (31 digitales) | Grupo3, JSON sin corregir (31 digitales) | Actual (31 digitales) |",
          "|---|---|---|---|"]
    actuales = [fraccion(digitales, "grilla_ok"), fraccion(digitales, "celdas_blancas_ok"), ocr(digitales),
                fraccion(digitales, "solucion_correcta"),
                str(sum(es(f, "incorrecta_presentada_como_correcta") for f in digitales))]
    for (nombre, viejo, grupo3), actual in zip(HISTORIAL, actuales):
        o.append(f"| {nombre} | {viejo} | {grupo3} | {actual} |")
    o.append("\nEntre \"Grupo3\" y \"Actual\" no cambió el código: la diferencia son los 2 JSON corregidos "
             "(`gris_08`, `gris_06`). `src/kakuro/` reproduce el notebook Grupo3 sin diferencias en 59 imágenes. "
             "El OCR del notebook viejo usa otro denominador: solo contaba las 17 imágenes con grilla correcta.\n")
    return "\n".join(o)


def leer_csv(ruta):
    """Lee un CSV en UTF-8 como lista de diccionarios (vacía si no existe)."""
    ruta = Path(ruta)
    if not ruta.exists():
        return []
    with open(ruta, encoding="utf-8") as archivo:
        return list(csv.DictReader(archivo))


def main(argumentos=None):
    """Lee los CSV de evaluar.py y escribe resumen.md en la misma carpeta."""
    parser = argparse.ArgumentParser(description="Genera resultados/resumen.md desde los CSV de evaluar.py.")
    parser.add_argument("--resultados", default="resultados", help="carpeta con metricas.csv y rechazo.csv")
    parser.add_argument("--condiciones", default="sin especificar",
                        help="versiones, máquina y commit con que se midió (se copia al resumen)")
    args = parser.parse_args(argumentos)
    carpeta = Path(args.resultados)
    filas = leer_csv(carpeta / "metricas.csv")
    if not filas:
        print(f"No hay {carpeta / 'metricas.csv'}: corre primero scripts/evaluar.py.")
        return 1
    texto = generar(filas, leer_csv(carpeta / "rechazo.csv"), args.condiciones)
    (carpeta / "resumen.md").write_text(texto, encoding="utf-8")
    print(f"Resumen guardado en {carpeta / 'resumen.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
