"""Pruebas de estructura.py: armado de grupos y exportación del estado inicial."""

import json
from pathlib import Path

import pytest

from kakuro.estructura import construir_grupos, exportar_json

GROUND_TRUTH = Path(__file__).resolve().parents[1] / "data" / "ground_truth"


def test_grupo_de_una_celda_lanza_error():
    # La pista (2, 1) apunta a una sola celda blanca.
    blancas = {(2, 2), (3, 2)}
    pistas = {(2, 1): {"derecha": [5]}, (1, 2): {"abajo": [9]}}
    with pytest.raises(ValueError, match="Grupo incompleto"):
        construir_grupos(blancas, pistas)


def test_cobertura_incompleta_lanza_error():
    # 2×2 blancas sin la pista vertical de la columna 3: (2, 3) y (3, 3)
    # quedan sin grupo vertical.
    blancas = {(2, 2), (2, 3), (3, 2), (3, 3)}
    pistas = {(1, 2): {"abajo": [15]}, (2, 1): {"derecha": [7]}, (3, 1): {"derecha": [13]}}
    with pytest.raises(ValueError, match="grupos horizontales y verticales completos"):
        construir_grupos(blancas, pistas)


def test_sin_celdas_blancas_lanza_error():
    with pytest.raises(ValueError, match="No se detectaron celdas blancas"):
        construir_grupos(set(), {})


def resultado_desde_ground_truth(nombre, sin_leer=()):
    """Arma un resultado como el de procesar_imagen a partir de un JSON del ground truth.

    Cada pista lleva su valor real como primer candidato y uno falso después.
    Las direcciones en `sin_leer` ((fila, columna, direccion)) quedan sin lectura.
    """
    gt = json.loads((GROUND_TRUTH / f"{nombre}.json").read_text(encoding="utf-8"))
    pistas = {}
    for pista in gt["pistas"]:
        fila, columna = pista["origen"]
        lecturas = {}
        for direccion in ("derecha", "abajo"):
            if pista[direccion] is not None:
                leida = (fila, columna, direccion) not in sin_leer
                lecturas[direccion] = [pista[direccion], 99] if leida else []
        pistas[(fila, columna)] = lecturas
    resultado = {"n": gt["n"], "blancas": {tuple(c) for c in gt["celdas_blancas"]}, "pistas": pistas}
    return gt, resultado


def normalizar_pistas(lista):
    """Pistas como set de tuplas, para comparar sin importar el orden."""
    return {(tuple(p["origen"]), p["derecha"], p["abajo"]) for p in lista}


@pytest.mark.parametrize("nombre", ["L_kakuro_03x03_clasico_06", "L_kakuro_07x07_clasico_01", "KC_kakuro_05x05_facil"])
def test_exportar_json_tiene_el_formato_del_ground_truth(nombre, tmp_path):
    gt, resultado = resultado_desde_ground_truth(nombre)
    ruta = tmp_path / "estado.json"
    estado = exportar_json(resultado, ruta, nombre_imagen=gt["imagen"])

    # Mismas claves que el ground truth, salvo la solución, más pistas_sin_lectura.
    assert set(estado) == {"imagen", "n", "celdas_blancas", "pistas", "pistas_sin_lectura"}
    assert estado["imagen"] == gt["imagen"]
    assert estado["n"] == gt["n"]
    assert estado["celdas_blancas"] == sorted(gt["celdas_blancas"])
    assert normalizar_pistas(estado["pistas"]) == normalizar_pistas(gt["pistas"])
    assert all(set(p) == {"origen", "derecha", "abajo"} for p in estado["pistas"])
    assert estado["pistas_sin_lectura"] == []
    # El archivo guardado es el mismo diccionario.
    assert json.loads(ruta.read_text(encoding="utf-8")) == estado


def test_exportar_json_marca_las_pistas_sin_lectura():
    _, resultado = resultado_desde_ground_truth("L_kakuro_03x03_clasico_06", sin_leer={(1, 3, "abajo")})
    estado = exportar_json(resultado)
    pista = next(p for p in estado["pistas"] if p["origen"] == [1, 3])
    assert pista["abajo"] is None
    assert estado["pistas_sin_lectura"] == [[1, 3, "abajo"]]


def test_exportar_json_sin_pistas_lanza_error():
    with pytest.raises(ValueError, match="tablero"):
        exportar_json({"estado": "NO_EJECUTADO", "error_etapa": "tablero", "error": "sin tablero"})
