"""Pruebas del modelo CP (sin OCR): resolver, rechazar pistas imposibles y no inventar pistas."""

from kakuro.estructura import construir_grupos
from kakuro.modelo_cp import resolver_csp

# L_kakuro_03x03_clasico_06: sumas 15 y 5 en las columnas, 7 y 13 en las filas.
#      .   15   5
#      7    6   1
#     13    9   4
BLANCAS = {(2, 2), (2, 3), (3, 2), (3, 3)}
SOLUCION = {(2, 2): 6, (2, 3): 1, (3, 2): 9, (3, 3): 4}


def pistas(abajo_2, abajo_3, derecha_2, derecha_3):
    """Pistas del 3×3 con los candidatos del OCR dados para cada suma."""
    return {
        (1, 2): {"abajo": abajo_2},
        (1, 3): {"abajo": abajo_3},
        (2, 1): {"derecha": derecha_2},
        (3, 1): {"derecha": derecha_3},
    }


def test_kakuro_3x3_conocido_se_resuelve_con_la_solucion_correcta():
    grupos = construir_grupos(BLANCAS, pistas([15], [5], [7], [13]))
    solucion, sumas, estadisticas = resolver_csp(BLANCAS, grupos)
    assert estadisticas["estado"] == "OPTIMAL"
    assert solucion == SOLUCION
    assert sumas == [15, 5, 7, 13]
    assert estadisticas["penalizacion"] == 0


def test_pistas_imposibles_devuelven_infeasible():
    # Las filas suman 7 + 13 = 20, pero las columnas leen 3 y 4. Incluso con
    # las variantes de CONFUSIONES (3 -> 5 u 8; 13 -> 15) no hay forma de que
    # las filas y las columnas sumen lo mismo.
    grupos = construir_grupos(BLANCAS, pistas([3], [4], [7], [13]))
    solucion, sumas, estadisticas = resolver_csp(BLANCAS, grupos)
    assert estadisticas["estado"] == "INFEASIBLE"
    assert solucion is None and sumas is None


def test_pista_sin_lectura_devuelve_pistas_sin_lectura_sin_llamar_al_solver():
    grupos = construir_grupos(BLANCAS, pistas([15], [], [7], [13]))
    solucion, sumas, estadisticas = resolver_csp(BLANCAS, grupos)
    assert estadisticas["estado"] == "PISTAS_SIN_LECTURA"
    assert solucion is None and sumas is None
    assert estadisticas["tiempo_solver_s"] is None
