"""
Unit tests for the Context Mapping Translator (Acciones OUA <--> Caudal L/s DGA).
"""

from src.domain.oua.context_translator import AccionesFlowTranslator


def test_traduccion_acciones_estandar():
    usuarios = [
        {"bocatoma_id": "boc-01", "nombre": "Canal Pirque", "acciones": 250.0},
        {"bocatoma_id": "boc-02", "nombre": "Canal Eyzaguirre", "acciones": 150.0},
    ]

    # Río tiene 4,000 L/s disponibles. Total estatuto = 1,000 acciones.
    # 4,000 / 1,000 = 4.0 L/s por acción.
    resultados = AccionesFlowTranslator.traducir_acciones_a_flujo(
        caudal_disponible_reparto_lps=4000.0,
        total_acciones_estatuto=1000.0,
        usuarios_acciones=usuarios
    )

    assert len(resultados) == 2
    r_pirque = resultados[0]
    assert r_pirque.valor_lps_por_accion == 4.0
    assert r_pirque.caudal_calculado_lps == 1000.0
    assert r_pirque.caudal_final_concedido_lps == 1000.0
    assert r_pirque.fue_topado_por_daa is False


def test_traduccion_con_invariante_tope_daa():
    usuarios = [
        {
            "bocatoma_id": "boc-agricola",
            "nombre": "Fundo San Miguel",
            "acciones": 50.0,
            "caudal_maximo_daa_lps": 400.0 # Tope legal máximo otorgado por la DGA
        }
    ]

    # Río en abundancia de deshielo: trae 10,000 L/s para 1,000 acciones -> 10.0 L/s por acción
    # 50 acciones * 10 = 500 L/s calculado, pero su DAA solo autoriza hasta 400 L/s.
    resultados = AccionesFlowTranslator.traducir_acciones_a_flujo(
        caudal_disponible_reparto_lps=10000.0,
        total_acciones_estatuto=1000.0,
        usuarios_acciones=usuarios
    )

    r = resultados[0]
    assert r.valor_lps_por_accion == 10.0
    assert r.caudal_calculado_lps == 500.0
    assert r.caudal_final_concedido_lps == 400.0 # Topado a 400
    assert r.fue_topado_por_daa is True
