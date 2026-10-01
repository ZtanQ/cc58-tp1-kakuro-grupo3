"""Modelo de Constraint Programming (OR-Tools CP-SAT) para resolver el Kakuro.

Las sumas leídas por OCR se tratan como variables de percepción: el solver
puede usar otra suma si la leída no forma un Kakuro válido, pagando un
costo. El objetivo es minimizar el costo total de corregir lecturas.
"""

from time import perf_counter

from ortools.sat.python import cp_model

from . import config

# Confusiones de dígitos que se aceptan como corrección del OCR.
# Clave: dígito leído. Valor: dígitos que podrían ser en realidad
# (por ejemplo, un "3" leído puede ser "5" u "8").
# PENDIENTE: el notebook no dice cómo se armó esta tabla; preguntar al equipo.
CONFUSIONES = {
    "0": "689",
    "1": "7",
    "2": "7",
    "3": "58",
    "4": "1",
    "5": "368",
    "6": "589",
    "7": "12",
    "8": "3569",
    "9": "68",
}


def dominios_pistas(grupos):
    """Calcula las sumas posibles de cada grupo y el costo de usar cada una.

    Para un grupo de L celdas la suma va de 1+2+...+L hasta la suma de los L
    dígitos más altos. Dentro de ese rango:
      - cada candidato del OCR cuesta su posición en el ranking (0, 1, 2, 3);
      - cada variante que sale de cambiar un dígito según CONFUSIONES cuesta
        COSTO_CONFUSION + posición del candidato original.
    Si una suma aparece por varios caminos, se queda el menor costo.

    Recibe la lista de grupos. Devuelve una lista (mismo orden) de
    diccionarios {suma: costo}. Un diccionario vacío significa que ningún
    candidato cayó en el rango válido.
    """
    dominios = []
    for g in grupos:
        L = len(g["celdas"])
        # 19 = 2·9 + 1: la suma de los L dígitos más altos es L·(19 − L) / 2.
        minimo, maximo = L * (L + 1) // 2, L * (2 * config.DIGITO_MAX + 1 - L) // 2
        costos = {}
        for rango, numero in enumerate(g["ocr"]):
            if minimo <= numero <= maximo:
                costos[numero] = min(costos.get(numero, config.COSTO_INICIAL), rango)
            # Probamos posibles confusiones de cifras con un costo mayor.
            for j, digito in enumerate(str(numero)):
                for nuevo in CONFUSIONES.get(digito, ""):
                    variante = int(str(numero)[:j] + nuevo + str(numero)[j + 1:])
                    if minimo <= variante <= maximo:
                        costos[variante] = min(costos.get(variante, config.COSTO_INICIAL), config.COSTO_CONFUSION + rango)
        dominios.append(costos)
    return dominios


def crear_variables(modelo, blancas, dominios):
    """Crea las variables del modelo.

    - x_f_c en DIGITO_MIN..DIGITO_MAX por cada celda blanca;
    - s_i por cada grupo, con dominio igual a las sumas posibles de dominios[i].

    Recibe el CpModel, el set de celdas blancas y los dominios.
    Devuelve una tupla (variables, sumas): un diccionario {(fila, columna): x}
    y una lista de variables de suma en el orden de los grupos.
    """
    variables = {
        c: modelo.NewIntVar(config.DIGITO_MIN, config.DIGITO_MAX, f"x_{c[0]}_{c[1]}") for c in sorted(blancas)
    }
    sumas = [
        modelo.NewIntVarFromDomain(cp_model.Domain.FromValues(sorted(d)), f"s_{i}")
        for i, d in enumerate(dominios)
    ]
    return variables, sumas


def agregar_restricciones(modelo, variables, sumas, grupos):
    """Agrega las reglas del Kakuro para cada grupo.

    - Suma: las celdas del grupo suman s_i.
    - AllDifferent: no se repiten dígitos dentro del grupo.

    Recibe el CpModel, las variables de celda, las de suma y los grupos.
    Modifica el modelo y no devuelve nada.
    """
    for g, s in zip(grupos, sumas):
        valores = [variables[c] for c in g["celdas"]]
        modelo.Add(sum(valores) == s)
        modelo.AddAllDifferent(valores)


def definir_objetivo(modelo, sumas, dominios):
    """Define el objetivo: minimizar el costo total de las sumas elegidas.

    Reificación: por cada suma posible v del grupo i se crea un booleano b_i_v
    y se agregan dos restricciones condicionadas (OnlyEnforceIf):
        b_i_v = 1  ->  s_i == v
        b_i_v = 0  ->  s_i != v
    Así b_i_v vale 1 exactamente cuando el solver elige la suma v, y el costo
    de esa suma se puede escribir de forma lineal como costo·b_i_v. Sin la
    reificación no habría manera lineal de cobrar un costo distinto por cada
    valor de s_i.

    Recibe el CpModel, las variables de suma y los dominios con sus costos.
    Modifica el modelo y no devuelve nada.
    """
    penalizaciones = []
    for i, (s, costos) in enumerate(zip(sumas, dominios)):
        for valor, costo in costos.items():
            elegido = modelo.NewBoolVar(f"b_{i}_{valor}")
            modelo.Add(s == valor).OnlyEnforceIf(elegido)
            modelo.Add(s != valor).OnlyEnforceIf(elegido.Not())
            penalizaciones.append(costo * elegido)
    modelo.Minimize(sum(penalizaciones))


def resolver_csp(blancas, grupos):
    """Construye el modelo, lo resuelve con CP-SAT y mide el tiempo.

    No inventa pistas: si algún grupo no tiene ninguna lectura del OCR,
    devuelve el estado PISTAS_SIN_LECTURA sin llamar al solver. Si ninguna
    lectura cae en el rango válido, devuelve PISTAS_FUERA_DE_RANGO.

    El solver usa TIEMPO_LIMITE, SEMILLA e HILOS de config: con semilla fija
    y un solo hilo el resultado es siempre el mismo.

    Recibe el set de celdas blancas y los grupos.
    Devuelve una tupla (solucion, sumas, estadisticas):
      - solucion: {(fila, columna): dígito}, o None si no hay solución;
      - sumas: lista de la suma elegida por grupo, o None;
      - estadisticas: diccionario con "estado", "tiempo_modelo_s",
        "tiempo_solver_s" y, si se llamó al solver, "ramas", "conflictos" y
        (con solución) "penalizacion".
    """
    inicio = perf_counter()
    if any(not g["ocr"] for g in grupos):
        return (
            None,
            None,
            {"estado": "PISTAS_SIN_LECTURA", "tiempo_solver_s": None, "tiempo_modelo_s": 0},
        )
    dominios = dominios_pistas(grupos)
    if any(not d for d in dominios):
        return (
            None,
            None,
            {
                "estado": "PISTAS_FUERA_DE_RANGO",
                "tiempo_solver_s": None,
                "tiempo_modelo_s": perf_counter() - inicio,
            },
        )
    modelo = cp_model.CpModel()
    variables, sumas = crear_variables(modelo, blancas, dominios)
    agregar_restricciones(modelo, variables, sumas, grupos)
    definir_objetivo(modelo, sumas, dominios)
    tiempo_modelo = perf_counter() - inicio
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = config.TIEMPO_LIMITE
    solver.parameters.num_search_workers = config.HILOS
    solver.parameters.random_seed = config.SEMILLA
    estado = solver.Solve(modelo)
    estadisticas = {
        "estado": solver.StatusName(estado),
        "tiempo_modelo_s": tiempo_modelo,
        "tiempo_solver_s": solver.WallTime(),
        "ramas": solver.NumBranches(),
        "conflictos": solver.NumConflicts(),
    }
    if estado not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None, None, estadisticas
    estadisticas["penalizacion"] = solver.ObjectiveValue()
    return (
        {c: solver.Value(v) for c, v in variables.items()},
        [solver.Value(s) for s in sumas],
        estadisticas,
    )
