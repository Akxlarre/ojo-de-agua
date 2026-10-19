"""
Unit tests for the Illegal Extraction Guardrail (MEE vs OrdenTurno).
"""

from src.domain.operation.models import EstadoOrdenTurno, OrdenTurno
from src.guardrails.illegal_extraction_guard import (
    IllegalExtractionGuardrail,
    LecturaSensorMEE,
)


def test_extraccion_conforme_a_derecho():
    orden = OrdenTurno(
        repartidor_autorizante="Repartidor Don Pedro",
        celador_id="celador-01",
        bocatoma_o_compuerta="boc-san-rafael",
        caudal_concedido_lps=500.0,
        horas_duracion=24.0,
        estado=EstadoOrdenTurno.PROGRAMADA
    )

    # Telemetría MEE marca 520 L/s (dentro del 10% de tolerancia: hasta 550 L/s)
    lectura = LecturaSensorMEE(
        bocatoma_id="boc-san-rafael",
        sensor_id="mee-001",
        caudal_instantaneo_lps=520.0
    )

    alerta = IllegalExtractionGuardrail.auditar_extraccion(lectura, [orden])
    assert alerta is None # No hay infracción


def test_extraccion_clandestina_sin_turno():
    # No existen órdenes de turno para la bocatoma pirata
    lectura = LecturaSensorMEE(
        bocatoma_id="boc-pirata",
        sensor_id="mee-999",
        caudal_instantaneo_lps=180.0 # Flujo detectado por el sensor MEE
    )

    alerta = IllegalExtractionGuardrail.auditar_extraccion(lectura, ordenes_activas=[])
    assert alerta is not None
    assert alerta.tipo_infraccion == "EXTRACCION_CLANDESTINA_SIN_TURNO"
    assert alerta.caudal_medido_lps == 180.0
    assert alerta.caudal_autorizado_lps == 0.0
    assert "Art. 173" in alerta.articulo_legal_violado


def test_sobreextraccion_excesiva():
    orden = OrdenTurno(
        repartidor_autorizante="Repartidor General",
        celador_id="celador-01",
        bocatoma_o_compuerta="boc-01",
        caudal_concedido_lps=200.0,
        horas_duracion=12.0,
        estado=EstadoOrdenTurno.PROGRAMADA
    )

    # El sensor MEE marca 350 L/s (muy por encima de los 200 L/s autorizados)
    lectura = LecturaSensorMEE(
        bocatoma_id="boc-01",
        sensor_id="mee-001",
        caudal_instantaneo_lps=350.0
    )

    alerta = IllegalExtractionGuardrail.auditar_extraccion(lectura, [orden])
    assert alerta is not None
    assert alerta.tipo_infraccion == "SOBREEXTRACCION_EXCESIVA"
    assert alerta.exceso_lps == 150.0
    assert "Art. 282" in alerta.articulo_legal_violado
