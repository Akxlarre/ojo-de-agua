"""
Unit and integration tests for Climate, Meteorology, and Megadrought Domain.
Validates CR2MET attributes, DGA meteorological integration, dynamic climate forcing in
diagnostic engine (I_disp), and REST API endpoints.
"""

import json
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from src.api.server import app
from src.domain.analytics.diagnostic_service import HolisticCuencaDiagnosticService

client = TestClient(app)
DATA_DIR = Path(__file__).parent.parent / "data"


def test_clima_datasets_integrity():
    """Verify that both station catalog and macrocuenca climate summaries are valid."""
    estaciones_file = DATA_DIR / "clima_estaciones_chile.json"
    cuencas_file = DATA_DIR / "clima_resumen_cuencas.json"

    assert estaciones_file.exists(), "clima_estaciones_chile.json must exist"
    assert cuencas_file.exists(), "clima_resumen_cuencas.json must exist"

    with open(estaciones_file, "r", encoding="utf-8") as f:
        estaciones = json.load(f)
    assert len(estaciones) >= 500, f"Expected at least 500 climate stations, got {len(estaciones)}"

    first_st = estaciones[0]
    required_st_fields = [
        "codigo_bna", "nombre", "cuenca_codigo",
        "precipitacion_media_anual_mm", "evapotranspiracion_potencial_anual_mm",
        "indice_aridez", "clasificacion_aridez",
        "fraccion_nieve_pct", "regimen_hidrologico", "deficit_megasequia_pct"
    ]
    for field in required_st_fields:
        assert field in first_st, f"Missing {field} in climate station data"

    with open(cuencas_file, "r", encoding="utf-8") as f:
        cuencas_clima = json.load(f)

    assert len(cuencas_clima) == 90, f"Expected 90 macrocuencas, got {len(cuencas_clima)}"
    maipo = next((c for c in cuencas_clima if c.get("cuenca_codigo") == "057"), None)
    assert maipo is not None, "Cuenca del Maipo (057) must exist in climate summary"

    assert maipo["cuenca_codigo"] == "057"
    assert maipo["evapotranspiracion_potencial_mm"] > 0
    assert maipo["deficit_megasequia_pct"] >= 20.0, "Central Chile must reflect severe megadrought deficit"
    assert maipo["total_estaciones_cr2met"] >= 1


def test_diagnostic_service_climate_forcing():
    """Verify that HolisticCuencaDiagnosticService factors in real climate data for I_disp calculation."""
    service = HolisticCuencaDiagnosticService()
    diag_maipo = service.calcular_diagnostico_cuenca("057")

    assert diag_maipo is not None
    metricas = diag_maipo["metricas_clave"]

    assert metricas["precipitacion_media_anual_mm"] > 0
    assert metricas["evapotranspiracion_potencial_mm"] > 0
    assert metricas["indice_aridez_medio"] > 0
    assert metricas["deficit_megasequia_pct"] >= 20.0

    # Ensure I_disp (disponibilidad_reserva) is properly bounded and computed
    subindices = diag_maipo["subindices"]
    assert "disponibilidad_reserva" in subindices
    i_disp = subindices["disponibilidad_reserva"]
    assert 0.0 <= i_disp <= 100.0, f"I_disp out of bounds: {i_disp}"

    # Critical findings should contain megadrought warning
    findings_str = " ".join(diag_maipo["hallazgos_criticos"])
    assert "Megasequía" in findings_str or "déficit" in findings_str or "CR2MET" in findings_str

    # Recommendations should cite Climate Change Framework Law 21.455
    recs_str = " ".join(diag_maipo["recomendaciones_gobernanza"])
    assert "21.455" in recs_str


def test_national_summary_climate_metrics():
    """Verify that the national overview contains macro climate and megadrought statistics."""
    service = HolisticCuencaDiagnosticService()
    resumen = service.obtener_resumen_nacional()

    assert "totales_estrategicos" in resumen
    totales = resumen["totales_estrategicos"]

    assert "deficit_megasequia_promedio_pct" in totales
    assert "cuencas_con_megasequia_severa" in totales
    assert totales["cuencas_con_megasequia_severa"] >= 20, "At least 20 cuencas should have severe megadrought"
    assert totales["deficit_megasequia_promedio_pct"] > 10.0


def test_api_clima_endpoints():
    """Test all REST API endpoints for climate and meteorological domain."""
    # 1. Resumen de Cuencas
    resp_resumen = client.get("/api/clima/resumen-cuencas")
    assert resp_resumen.status_code == 200
    resumen_data = resp_resumen.json()
    assert isinstance(resumen_data, list)
    assert any(c.get("cuenca_codigo") == "057" for c in resumen_data)
    assert any(c.get("cuenca_codigo") == "054" for c in resumen_data)

    # 2. Estaciones Meteorológicas Catálogo
    resp_estaciones = client.get("/api/clima/estaciones")
    assert resp_estaciones.status_code == 200
    estaciones_resp = resp_estaciones.json()
    assert "estaciones_climaticas" in estaciones_resp
    estaciones_list = estaciones_resp["estaciones_climaticas"]
    assert len(estaciones_list) > 0

    # Filter by cuenca
    resp_maipo_st = client.get("/api/clima/estaciones?cuenca=057&limit=50")
    assert resp_maipo_st.status_code == 200
    maipo_st = resp_maipo_st.json()["estaciones_climaticas"]
    assert len(maipo_st) > 0
    for st in maipo_st:
        assert st["cuenca_codigo"] == "057"

    # Filter by regime
    resp_nival = client.get("/api/clima/estaciones?regimen=Nival&limit=20")
    assert resp_nival.status_code == 200
    nival_st = resp_nival.json()["estaciones_climaticas"]
    assert len(nival_st) > 0
    for st in nival_st:
        assert st["regimen_hidrologico"] == "Nival"

    # 3. Ficha Climática por Cuenca
    resp_cuenca_057 = client.get("/api/clima/cuenca/057")
    assert resp_cuenca_057.status_code == 200
    c057 = resp_cuenca_057.json()
    assert c057["cuenca_codigo"] == "057"
    assert "precipitacion_media_anual_mm" in c057
    assert "deficit_megasequia_pct" in c057

    # 4. Error 404 for unknown cuenca
    resp_404 = client.get("/api/clima/cuenca/999")
    assert resp_404.status_code == 404
