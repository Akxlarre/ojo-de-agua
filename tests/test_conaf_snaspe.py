"""
Unit and Integration Tests for CONAF / SNASPE Áreas Silvestres Protegidas.
Verifies headwater protected areas, basin aggregates, knowledge graph nodes, and FastAPI REST endpoints.
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.server import app

client = TestClient(app)
DATA_DIR = Path(__file__).parent.parent / "data"


def test_conaf_snaspe_integrity():
    """Valida la integridad del catastro SNASPE de áreas silvestres protegidas."""
    snaspe_file = DATA_DIR / "conaf_snaspe_chile.json"
    assert snaspe_file.exists(), "conaf_snaspe_chile.json debe existir."

    with open(snaspe_file, "r", encoding="utf-8") as f:
        snaspe = json.load(f)

    assert len(snaspe) >= 100, f"Se esperaban al menos 100 unidades SNASPE, encontradas {len(snaspe)}"

    sample = snaspe[0]
    required_keys = [
        "id", "nombre", "categoria", "region", "superficie_ha",
        "superficie_km2", "decreto_creacion", "cuenca_codigo", "cuenca_nombre"
    ]
    for k in required_keys:
        assert k in sample, f"Clave requerida '{k}' no encontrada en unidad SNASPE."

    assert sample["superficie_ha"] > 0


def test_conaf_snaspe_resumen_cuencas_integrity():
    """Valida la agregación de cabeceras protegidas por macrocuenca."""
    resumen_file = DATA_DIR / "conaf_snaspe_resumen_cuencas.json"
    assert resumen_file.exists(), "conaf_snaspe_resumen_cuencas.json debe existir."

    with open(resumen_file, "r", encoding="utf-8") as f:
        resumen = json.load(f)

    assert len(resumen) >= 40, f"Se esperaban al menos 40 cuencas con áreas protegidas, encontradas {len(resumen)}"

    for c in resumen:
        assert c["total_areas_protegidas"] >= 1
        assert c["superficie_total_ha"] > 0


def test_knowledge_graph_ecosystems_preservation_context():
    """Valida la presencia de nodos AreaSilvestreProtegida y aristas PROTEGE_CABECERA_CUENCA en el grafo."""
    kg_file = DATA_DIR / "knowledge_graph_chile.json"
    assert kg_file.exists(), "knowledge_graph_chile.json debe existir."

    with open(kg_file, "r", encoding="utf-8") as f:
        kg = json.load(f)

    nodes = kg.get("nodes", [])
    edges = kg.get("edges", [])

    snaspe_nodes = [n for n in nodes if n.get("label") == "AreaSilvestreProtegida"]
    assert len(snaspe_nodes) >= 100, f"Se esperaban al menos 100 nodos AreaSilvestreProtegida, encontrados {len(snaspe_nodes)}"
    assert all(n.get("bounded_context") == "ecosystems_preservation" for n in snaspe_nodes)

    protege_edges = [e for e in edges if e.get("relation_type") == "PROTEGE_CABECERA_CUENCA"]
    assert len(protege_edges) >= 100, f"Se esperaban al menos 100 aristas PROTEGE_CABECERA_CUENCA, encontradas {len(protege_edges)}"


def test_api_snaspe_resumen_cuencas():
    """Valida el endpoint GET /api/snaspe/resumen-cuencas."""
    response = client.get("/api/snaspe/resumen-cuencas")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 40

    first_cuenca = data[0]["cuenca_codigo"]
    res_single = client.get(f"/api/snaspe/resumen-cuencas?cuenca={first_cuenca}")
    assert res_single.status_code == 200
    assert len(res_single.json()) == 1


def test_api_snaspe_areas_listing():
    """Valida el endpoint GET /api/snaspe/areas con filtros."""
    response = client.get("/api/snaspe/areas?limit=10")
    assert response.status_code == 200
    res = response.json()
    assert "total_coincidentes" in res
    assert len(res["areas_protegidas"]) == 10

    # Filtro por categoría Parque Nacional
    res_parque = client.get("/api/snaspe/areas?categoria=Parque Nacional")
    assert res_parque.status_code == 200
    parque_data = res_parque.json()
    assert parque_data["total_coincidentes"] >= 40
    for p in parque_data["areas_protegidas"]:
        assert "Parque Nacional" in p["categoria"]


def test_api_snaspe_area_detail():
    """Valida el endpoint GET /api/snaspe/area/{id_o_nombre} y error 404."""
    list_res = client.get("/api/snaspe/areas?limit=1")
    area = list_res.json()["areas_protegidas"][0]
    aid = area["id"]

    res_ok = client.get(f"/api/snaspe/area/{aid}")
    assert res_ok.status_code == 200
    detail = res_ok.json()
    assert detail["id"] == aid
    assert "categoria" in detail

    # 404
    res_404 = client.get("/api/snaspe/area/parque_inexistente_99999")
    assert res_404.status_code == 404
