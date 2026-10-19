"""
Unit and Integration Tests for HolisticCuencaDiagnosticService and Diagnostic API.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.server import app
from src.domain.analytics.diagnostic_service import HolisticCuencaDiagnosticService

client = TestClient(app)


def test_diagnostic_service_initialization():
    service = HolisticCuencaDiagnosticService()
    resumen = service.obtener_resumen_nacional()

    assert resumen["total_cuencas_evaluadas"] >= 80
    assert 0.0 <= resumen["indice_seguridad_hidrica_nacional_promedio"] <= 100.0
    assert "distribucion_semaforo" in resumen
    assert "totales_estrategicos" in resumen
    assert len(resumen["top_5_cuencas_mas_criticas"]) == 5
    assert len(resumen["top_5_cuencas_mas_sostenibles"]) == 5


def test_diagnostic_service_cuenca_maipo():
    service = HolisticCuencaDiagnosticService()
    diag = service.calcular_diagnostico_cuenca("057")  # Río Maipo

    assert diag is not None
    assert diag["codigo_dga"] == "057"
    assert "Maipo" in diag["nombre"]
    assert 0.0 <= diag["indice_seguridad_hidrica"] <= 100.0
    assert diag["clasificacion"] in ["CRÍTICO", "VULNERABLE", "SOSTENIBLE"]
    assert len(diag["subindices"]) == 5
    assert len(diag["hallazgos_criticos"]) >= 1
    assert len(diag["recomendaciones_gobernanza"]) >= 1
    assert diag["metricas_clave"]["glaciares_total"] > 1000


def test_diagnostic_service_cuenca_inexistente():
    service = HolisticCuencaDiagnosticService()
    diag = service.calcular_diagnostico_cuenca("99999")
    assert diag is None


def test_api_diagnostico_resumen():
    response = client.get("/api/diagnostico/resumen")
    assert response.status_code == 200
    data = response.json()
    assert "total_cuencas_evaluadas" in data
    assert "indice_seguridad_hidrica_nacional_promedio" in data
    assert "distribucion_semaforo" in data


def test_api_diagnostico_cuencas_ranking():
    response = client.get("/api/diagnostico/cuencas?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "total_coincidentes" in data
    assert "cuencas" in data
    assert len(data["cuencas"]) <= 10

    # Las primeras cuencas deben ser más críticas (menor ISH)
    primeras = data["cuencas"]
    if len(primeras) >= 2:
        assert primeras[0]["indice_seguridad_hidrica"] <= primeras[-1]["indice_seguridad_hidrica"]


def test_api_diagnostico_cuencas_filtro_semaforo():
    response = client.get("/api/diagnostico/cuencas?clasificacion=CRITICO")
    assert response.status_code == 200
    data = response.json()
    for c in data["cuencas"]:
        assert c["clasificacion"] == "CRÍTICO"


def test_api_diagnostico_cuenca_detalle():
    response = client.get("/api/diagnostico/cuenca/057")
    assert response.status_code == 200
    data = response.json()
    assert data["codigo_dga"] == "057"
    assert "subindices" in data
    assert "metricas_clave" in data
    assert "hallazgos_criticos" in data
    assert "recomendaciones_gobernanza" in data


def test_api_diagnostico_cuenca_no_encontrada():
    response = client.get("/api/diagnostico/cuenca/99999")
    assert response.status_code == 404
