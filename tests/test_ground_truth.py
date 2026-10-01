"""Todos los JSON de data/ground_truth/ pasan el verificador (sumas, cobertura, unicidad)."""

from pathlib import Path

import pytest

from verificar_ground_truth import validar_tablero, verificar_carpeta

DATOS = Path(__file__).resolve().parents[1] / "data"
RESULTADO = verificar_carpeta(DATOS)


def test_hay_json_para_verificar():
    assert len(RESULTADO) >= 58


@pytest.mark.parametrize("nombre", sorted(RESULTADO))
def test_json_del_ground_truth_es_valido(nombre):
    assert RESULTADO[nombre] == []


def test_el_verificador_detecta_un_tablero_roto():
    # 3×3 con la suma de una fila cambiada: deja de cuadrar con la solución.
    roto = {
        "n": 3,
        "celdas_blancas": [[2, 2], [2, 3], [3, 2], [3, 3]],
        "pistas": [
            {"origen": [1, 2], "derecha": None, "abajo": 15},
            {"origen": [1, 3], "derecha": None, "abajo": 5},
            {"origen": [2, 1], "derecha": 8, "abajo": None},
            {"origen": [3, 1], "derecha": 13, "abajo": None},
        ],
        "solucion": {"2,2": 6, "2,3": 1, "3,2": 9, "3,3": 4},
    }
    assert any("no suma 8" in e for e in validar_tablero(roto))


def test_el_verificador_detecta_mas_de_una_solucion():
    # 2×2 con sumas 3/3 en filas y 3/3 en columnas: 1-2/2-1 y 2-1/1-2.
    ambiguo = {
        "n": 3,
        "celdas_blancas": [[2, 2], [2, 3], [3, 2], [3, 3]],
        "pistas": [
            {"origen": [1, 2], "derecha": None, "abajo": 3},
            {"origen": [1, 3], "derecha": None, "abajo": 3},
            {"origen": [2, 1], "derecha": 3, "abajo": None},
            {"origen": [3, 1], "derecha": 3, "abajo": None},
        ],
        "solucion": {"2,2": 1, "2,3": 2, "3,2": 2, "3,3": 1},
    }
    assert validar_tablero(ambiguo) == ["tiene más de una solución"]
