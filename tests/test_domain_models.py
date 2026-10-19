"""
Unit tests for Chilean Water DDD Domain Models and Invariants.
"""

import pytest
from src.domain.legal.models import DAA, ClaseDerecho, InscripcionCBR, TipoAprovechamiento
from src.domain.oua.models import AccionistaOUA, AsociacionCanalistas, JuntaVigilancia
from src.domain.physical.models import Canal, MarcoPartidor, TipoCanal
from src.domain.operation.models import BalanceHidricoSeccion, Celador, OrdenTurno


def test_daa_invariants_cbr_and_cpa():
    # DAA without CBR or CPA registration should trigger Ley 21.435 invariant warnings
    daa = DAA(
        codigo_dga="RES-DGA-2023-450",
        titular_nombre="Agrícola El Maipo SpA",
        titular_rut="76.123.456-7",
        tipo=TipoAprovechamiento.CONSUNTIVO,
        clase=ClaseDerecho.PERMANENTE,
        caudal_lps=120.5,
        inscrito_cpa=False,
        inscripcion_cbr=None,
    )
    violations = daa.check_invariants()
    assert any("Catastro Público de Aguas" in v for v in violations)
    assert any("CBR competente" in v for v in violations)


def test_asociacion_canalistas_padron_consistency():
    # If padron sum doesn't match total_acciones, invariant fails
    ac = AsociacionCanalistas(
        nombre="Asociación Canalistas Canal San Carlos",
        canal_matriz="Canal San Carlos",
        bocatoma_nombre="Bocatoma San Carlos",
        total_acciones=100.0,
        padron_accionistas=[
            AccionistaOUA(rut="11.111.111-1", nombre="Fundo Los Lingues", numero_acciones=40.0),
            AccionistaOUA(rut="22.222.222-2", nombre="Agrícola El Peumo", numero_acciones=50.0),
        ] # Sums to 90.0, but total is 100.0!
    )
    violations = ac.check_invariants()
    assert len(violations) == 1
    assert "no coincide con el total estatutario" in violations[0]


def test_marco_partidor_percentage_invariant():
    # Must sum to exactly 100%
    marco_invalido = MarcoPartidor(
        nombre="Partidor La Puntilla",
        canal_origen_id="canal-001",
        distribucion_porcentual={"Ramal A": 60.0, "Ramal B": 30.0} # Sums to 90%!
    )
    violations = marco_invalido.check_invariants()
    assert len(violations) == 1
    assert "debe ser exactamente 100.0%" in violations[0]


def test_balance_hidrico_mass_conservation():
    # River section has 5 m3/s influx. Demands: 4 m3/s to Canal A + 2 m3/s ecological minimum = 6 m3/s -> Deficit!
    balance = BalanceHidricoSeccion(
        seccion_id="sec-maipo-1",
        caudal_afluente_m3s=5.0,
        caudal_ecologico_minimo_m3s=2.0,
        extracciones_bocatomas_m3s={"Bocatoma San Carlos": 4.0}
    )
    violations = balance.check_invariants()
    assert len(violations) == 1
    assert "Violación Balance de Masa" in violations[0]
