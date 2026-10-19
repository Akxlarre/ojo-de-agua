"""
Unit tests for the ProrrateoLegalService (Ley 21.435, Art. 5 bis & Art. 18).
"""

import pytest
from src.domain.operation.prorrateo_service import (
    DemandaCanal,
    EstadoEscasez,
    ProrrateoLegalService,
)


def test_prorrateo_abundancia_sobrante_para_eventuales():
    demandas = [
        DemandaCanal(
            bocatoma_id="boc-01",
            nombre_canal="Canal San Carlos (Aguas Andinas & Riego)",
            caudal_consumo_humano_lps=1000.0,
            caudal_permanente_autorizado_lps=5000.0,
            caudal_eventual_autorizado_lps=2000.0
        ),
        DemandaCanal(
            bocatoma_id="boc-02",
            nombre_canal="Canal Pirque",
            caudal_consumo_humano_lps=0.0,
            caudal_permanente_autorizado_lps=3000.0,
            caudal_eventual_autorizado_lps=1000.0
        )
    ]

    # Río trae 14,000 L/s. Ecológico mínimo: 2,000 L/s.
    # Total humano: 1,000 L/s. Total permanente: 8,000 L/s. Total eventual: 3,000 L/s.
    # Post humano y ecológico: 14,000 - 1,000 - 2,000 = 11,000 L/s.
    # Permanentes toman 8,000 L/s -> Sobran 3,000 L/s -> Eventuales reciben 100%!
    resultado = ProrrateoLegalService.calcular_distribucion(
        caudal_afluente_lps=14000.0,
        caudal_ecologico_minimo_lps=2000.0,
        demandas_canales=demandas
    )

    assert resultado.factor_prorrateo_permanente == 1.0
    assert resultado.factor_prorrateo_eventual == 1.0
    assert resultado.estado_cuenca == EstadoEscasez.ABUNDANCIA
    assert len(resultado.invariantes_violadas) == 0


def test_prorrateo_severo_protege_consumo_humano_y_bloquea_eventuales():
    demandas = [
        DemandaCanal(
            bocatoma_id="boc-apr",
            nombre_canal="Canal APR Melipilla",
            caudal_consumo_humano_lps=500.0, # Agua potable rural
            caudal_permanente_autorizado_lps=1500.0,
            caudal_eventual_autorizado_lps=1000.0
        ),
        DemandaCanal(
            bocatoma_id="boc-agricola",
            nombre_canal="Canal Agrícola Los Maquis",
            caudal_consumo_humano_lps=0.0,
            caudal_permanente_autorizado_lps=4500.0,
            caudal_eventual_autorizado_lps=2000.0
        )
    ]

    # Río trae solo 4,000 L/s por sequía estival.
    # Ecológico: 500 L/s.
    # Humano toma 500 L/s (100% satisfecho).
    # Remanente productivo: 4,000 - 500 (humano) - 500 (ecológico) = 3,000 L/s.
    # Demanda permanente: 1,500 + 4,500 = 6,000 L/s.
    # Factor permanente alpha = 3,000 / 6,000 = 0.50 (50%).
    # Factor eventual beta = 0.0 (estrictamente bloqueado por Art. 18 CdA).
    resultado = ProrrateoLegalService.calcular_distribucion(
        caudal_afluente_lps=4000.0,
        caudal_ecologico_minimo_lps=500.0,
        demandas_canales=demandas
    )

    assert resultado.factor_prorrateo_permanente == 0.50
    assert resultado.factor_prorrateo_eventual == 0.0
    assert resultado.estado_cuenca == EstadoEscasez.PRORRATEO_SEVERO

    # El canal APR recibió 100% de su agua humana (500 L/s) + 50% de su permanente (750 L/s)
    asig_apr = [a for a in resultado.asignaciones_por_canal if a.bocatoma_id == "boc-apr"][0]
    assert asig_apr.caudal_consumo_humano_entregado_lps == 500.0
    assert asig_apr.caudal_permanente_entregado_lps == 750.0
    assert asig_apr.caudal_eventual_entregado_lps == 0.0


def test_prorrateo_crisis_humana_extrema():
    demandas = [
        DemandaCanal(
            bocatoma_id="boc-ciudad",
            nombre_canal="Bocatoma Ciudad",
            caudal_consumo_humano_lps=1200.0,
            caudal_permanente_autorizado_lps=2000.0
        )
    ]

    # El río trae solo 600 L/s y la ciudad necesita 1,200 L/s para beber
    resultado = ProrrateoLegalService.calcular_distribucion(
        caudal_afluente_lps=600.0,
        caudal_ecologico_minimo_lps=200.0,
        demandas_canales=demandas
    )

    assert resultado.estado_cuenca == EstadoEscasez.EMERGENCIA_CONSUMO_HUMANO
    assert resultado.factor_prorrateo_permanente == 0.0
    assert len(resultado.invariantes_violadas) > 0
    assert "INV-LEGAL-CRISIS" in resultado.invariantes_violadas[0]


def test_prorrateo_rechaza_caudales_negativos():
    demandas = [
        DemandaCanal(
            bocatoma_id="boc-01",
            nombre_canal="Canal Test",
            caudal_consumo_humano_lps=100.0,
            caudal_permanente_autorizado_lps=500.0
        )
    ]
    with pytest.raises(ValueError, match="caudal afluente no puede ser negativo"):
        ProrrateoLegalService.calcular_distribucion(
            caudal_afluente_lps=-100.0,
            caudal_ecologico_minimo_lps=50.0,
            demandas_canales=demandas
        )

    with pytest.raises(ValueError, match="caudal ecológico mínimo no puede ser negativo"):
        ProrrateoLegalService.calcular_distribucion(
            caudal_afluente_lps=1000.0,
            caudal_ecologico_minimo_lps=-50.0,
            demandas_canales=demandas
        )

