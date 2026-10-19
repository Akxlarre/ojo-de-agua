"""
Unit tests for Event Sourcing & CQRS in Water Operations.
"""

from src.domain.operation.event_sourcing import (
    BitacoraCeladorProjection,
    CompuertaAggregate,
    CompuertaAjustadaEvent,
    EventStore,
)


def test_compuerta_event_sourcing_lifecycle():
    event_store = EventStore()

    # Create new gate aggregate
    compuerta = CompuertaAggregate(
        id="boc-san-carlos",
        bocatoma_id="boc-san-carlos",
        nombre="Compuerta Principal San Carlos"
    )

    # Initial state
    assert compuerta.apertura_actual_porcentaje == 0.0
    assert compuerta.caudal_actual_lps == 0.0

    # 1. Celador opens gate to 30% under order 001
    ev1 = compuerta.ajustar(
        celador_id="celador-perez",
        orden_turno_id="ORD-2026-001",
        apertura_porcentaje=30.0,
        caudal_resultante_lps=12500.0
    )
    event_store.append(ev1)

    assert compuerta.apertura_actual_porcentaje == 30.0
    assert compuerta.caudal_actual_lps == 12500.0
    assert compuerta.ultimo_celador_operador == "celador-perez"

    # 2. Celador opens gate further to 60% under order 002
    ev2 = compuerta.ajustar(
        celador_id="celador-perez",
        orden_turno_id="ORD-2026-002",
        apertura_porcentaje=60.0,
        caudal_resultante_lps=25000.0
    )
    event_store.append(ev2)

    assert compuerta.apertura_actual_porcentaje == 60.0
    assert compuerta.caudal_actual_lps == 25000.0

    # 3. Test Rehydration: completely fresh instance replaying event stream
    events = event_store.get_events_for_aggregate("boc-san-carlos")
    assert len(events) == 2

    rehydrated = CompuertaAggregate.rehydrate(
        bocatoma_id="boc-san-carlos",
        nombre="Compuerta Principal San Carlos",
        events=events
    )

    assert rehydrated.apertura_actual_porcentaje == 60.0
    assert rehydrated.caudal_actual_lps == 25000.0
    assert rehydrated.ultimo_celador_operador == "celador-perez"
    assert rehydrated.ultima_orden_id == "ORD-2026-002"


def test_cqrs_bitacora_celador_projection():
    event_store = EventStore()
    compuerta = CompuertaAggregate(id="boc-01", bocatoma_id="boc-01", nombre="Bocatoma 1")

    # Maniobras de Don Juan Pérez
    ev1 = compuerta.ajustar("celador-perez", "ORD-1", 20.0, 5000.0)
    event_store.append(ev1)
    ev2 = compuerta.ajustar("celador-perez", "ORD-2", 40.0, 10000.0)
    event_store.append(ev2)

    # Maniobra de otro celador (Don Luis Gómez)
    ev3 = compuerta.ajustar("celador-gomez", "ORD-3", 10.0, 2500.0)
    event_store.append(ev3)

    # CQRS Projection para Pérez
    bitacora_perez = BitacoraCeladorProjection.generar_reporte(event_store, "celador-perez")
    assert len(bitacora_perez) == 2
    assert bitacora_perez[0]["orden"] == "ORD-1"
    assert bitacora_perez[1]["orden"] == "ORD-2"

    # CQRS Projection para Gómez
    bitacora_gomez = BitacoraCeladorProjection.generar_reporte(event_store, "celador-gomez")
    assert len(bitacora_gomez) == 1
    assert bitacora_gomez[0]["orden"] == "ORD-3"
