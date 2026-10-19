"""
Unit and integration tests for the Inventario Público de Glaciares de Chile (DGA - IPG 2022).
Validates dataset integrity, cryosphere bounded context in the Knowledge Graph, and REST API endpoints.
"""

import json
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from src.api.server import app

client = TestClient(app)
DATA_DIR = Path(__file__).parent.parent / "data"


def test_glaciares_dataset_integrity():
    gla_file = DATA_DIR / "glaciares_chile.json"
    assert gla_file.exists(), "glaciares_chile.json must exist"

    with open(gla_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert len(data) == 26180, f"Expected exactly 26,180 glaciares, got {len(data)}"
    first = data[0]
    assert "codigo_glaciar" in first
    assert "clasificacion" in first
    assert "area_km2" in first
    assert "volumen_km3" in first
    assert "equivalente_agua_km3" in first
    assert "cuenca_codigo" in first
    assert "coordenadas" in first
    assert len(first["coordenadas"]) == 2
    assert "Art. 5 bis" in first["proteccion_legal"]


def test_glaciares_resumen_cuencas_integrity():
    resumen_file = DATA_DIR / "glaciares_resumen_cuencas.json"
    assert resumen_file.exists(), "glaciares_resumen_cuencas.json must exist"

    with open(resumen_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert len(data) == 55, f"Expected 55 basins with glaciares, got {len(data)}"
    # Check that Maipo (057) is present
    maipo = next((c for c in data if c["cuenca_codigo"] == "057"), None)
    assert maipo is not None, "Cuenca 057 (Maipo) must have glacier reserves"
    assert maipo["glaciares_count"] > 1000
    assert maipo["superficie_total_km2"] > 300.0


def test_knowledge_graph_cryosphere_context():
    graph_file = DATA_DIR / "knowledge_graph_chile.json"
    assert graph_file.exists(), "knowledge_graph_chile.json must exist"

    with open(graph_file, "r", encoding="utf-8") as f:
        graph = json.load(f)

    glaciar_nodes = [n for n in graph["nodes"] if n.get("label") == "Glaciar"]
    assert len(glaciar_nodes) >= 2000, f"Expected at least 2,000 strategic glacier nodes, got {len(glaciar_nodes)}"

    alimenta_edges = [e for e in graph["edges"] if e.get("relation_type") == "ALIMENTA_CUENCA"]
    assert len(alimenta_edges) >= 2000, f"Expected at least 2,000 ALIMENTA_CUENCA edges, got {len(alimenta_edges)}"


def test_api_glaciares_endpoint():
    resp = client.get("/api/glaciares?limit=50")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_coincidentes"] == 26180
    assert len(data["glaciares"]) == 50

    # Filter by Cuenca 057 (Maipo)
    resp_maipo = client.get("/api/glaciares?cuenca=057&limit=100")
    assert resp_maipo.status_code == 200
    maipo_data = resp_maipo.json()
    assert maipo_data["total_coincidentes"] > 1000
    for g in maipo_data["glaciares"]:
        assert g["cuenca_codigo"] == "057"

    # Filter by name
    resp_nom = client.get("/api/glaciares?nombre=Parinacota")
    assert resp_nom.status_code == 200
    nom_data = resp_nom.json()
    assert nom_data["total_coincidentes"] >= 1
    assert "parinacota" in nom_data["glaciares"][0]["nombre"].lower()


def test_api_glaciares_resumen_cuencas():
    resp = client.get("/api/glaciares/resumen-cuencas")
    assert resp.status_code == 200
    cuencas = resp.json()
    assert len(cuencas) == 55

    # Filter by single basin
    resp_single = client.get("/api/glaciares/resumen-cuencas?cuenca=057")
    assert resp_single.status_code == 200
    single = resp_single.json()
    assert len(single) == 1
    assert single[0]["cuenca_codigo"] == "057"
    assert len(single[0]["glaciares_principales"]) > 0
