"""
Unit and integration tests for the National Irrigation Canals Dataset (CNR / CIREN / IDE Minagri).
Validates dataset integrity, infrastructure bounded context in the Knowledge Graph, and REST API endpoints.
"""

import json
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from src.api.server import app

client = TestClient(app)
DATA_DIR = Path(__file__).parent.parent / "data"


def test_canales_ciren_dataset_integrity():
    can_file = DATA_DIR / "canales_riego_chile.json"
    assert can_file.exists(), "canales_riego_chile.json must exist"

    with open(can_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert len(data) == 12233, f"Expected exactly 12,233 canales, got {len(data)}"
    first = data[0]
    assert "codigo_canal" in first
    assert "nombre" in first
    assert "tipo_canal" in first
    assert "longitud_km" in first
    assert "centroide" in first
    assert "trazado_simplificado" in first
    assert len(first["trazado_simplificado"]) >= 1


def test_canales_resumen_cuencas_integrity():
    resumen_file = DATA_DIR / "canales_resumen_cuencas.json"
    assert resumen_file.exists(), "canales_resumen_cuencas.json must exist"

    with open(resumen_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert len(data) == 44, f"Expected 44 basins with irrigation canals, got {len(data)}"
    # Check that Maipo (057) is present
    maipo = next((c for c in data if c["cuenca_codigo"] == "057"), None)
    assert maipo is not None, "Cuenca 057 (Maipo) must have irrigation canals"
    assert maipo["canales_count"] > 800
    assert maipo["longitud_total_km"] > 2000.0


def test_knowledge_graph_infrastructure_context():
    graph_file = DATA_DIR / "knowledge_graph_chile.json"
    assert graph_file.exists(), "knowledge_graph_chile.json must exist"

    with open(graph_file, "r", encoding="utf-8") as f:
        graph = json.load(f)

    infra_nodes = [n for n in graph["nodes"] if n.get("bounded_context") == "infrastructure"]
    assert len(infra_nodes) >= 2200, f"Expected at least 2,200 strategic canal nodes, got {len(infra_nodes)}"

    conduce_edges = [e for e in graph["edges"] if e.get("relation_type") == "CONDUCE_EN_CUENCA"]
    assert len(conduce_edges) >= 2200, f"Expected at least 2,200 CONDUCE_EN_CUENCA edges, got {len(conduce_edges)}"


def test_api_canales_riego_endpoint():
    resp = client.get("/api/canales-riego?limit=50")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_coincidentes"] == 12233
    assert len(data["canales"]) == 50

    # Filter by Cuenca 057 (Maipo)
    resp_maipo = client.get("/api/canales-riego?cuenca=057&limit=100")
    assert resp_maipo.status_code == 200
    maipo_data = resp_maipo.json()
    assert maipo_data["total_coincidentes"] > 800
    for c in maipo_data["canales"]:
        assert c["cuenca_codigo"] == "057"

    # Filter by Junta de Vigilancia
    resp_jv = client.get("/api/canales-riego?junta_vigilancia=Maule")
    assert resp_jv.status_code == 200
    jv_data = resp_jv.json()
    assert jv_data["total_coincidentes"] > 400
    for c in jv_data["canales"]:
        assert "maule" in c["junta_vigilancia"].lower()

    # Filter by source river
    resp_fuente = client.get("/api/canales-riego?fuente=Mapocho")
    assert resp_fuente.status_code == 200
    fuente_data = resp_fuente.json()
    assert fuente_data["total_coincidentes"] > 50


def test_api_canales_resumen_cuencas():
    resp = client.get("/api/canales-riego/resumen-cuencas")
    assert resp.status_code == 200
    cuencas = resp.json()
    assert len(cuencas) == 44

    # Filter by single basin
    resp_single = client.get("/api/canales-riego/resumen-cuencas?cuenca=057")
    assert resp_single.status_code == 200
    single = resp_single.json()
    assert len(single) == 1
    assert single[0]["cuenca_codigo"] == "057"
    assert len(single[0]["canales_matrices_principales"]) > 0
