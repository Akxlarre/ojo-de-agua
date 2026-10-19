"""
Unit and Integration Tests for SERNAGEOMIN Depósitos de Relaves Mineros (2025).
Verifies mining tailing risks, basin receptor allocations, knowledge graph nodes, and FastAPI REST endpoints.
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.server import app

client = TestClient(app)
DATA_DIR = Path(__file__).parent.parent / "data"


def test_sernageomin_relaves_integrity():
    """Valida la integridad del catastro de depósitos de relaves SERNAGEOMIN."""
    relaves_file = DATA_DIR / "sernageomin_relaves_chile.json"
    assert relaves_file.exists(), "sernageomin_relaves_chile.json debe existir."

    with open(relaves_file, "r", encoding="utf-8") as f:
        relaves = json.load(f)

    assert len(relaves) >= 800, f"Se esperaban al menos 800 relaves, encontrados {len(relaves)}"

    sample = relaves[0]
    required_keys = [
        "id", "codigo_deposito", "nombre_faena", "nombre_instalacion",
        "titular_minero", "tipo_deposito", "estado_operativo", "clasificacion_riesgo",
        "cuenca_codigo", "cuenca_nombre", "coordenadas"
    ]
    for k in required_keys:
        assert k in sample, f"Clave requerida '{k}' no encontrada en depósito de relaves."

    assert sample["coordenadas"] is not None


def test_sernageomin_resumen_cuencas_integrity():
    """Valida la agregación de pasivos y riesgos mineros por macrocuenca."""
    resumen_file = DATA_DIR / "sernageomin_relaves_resumen_cuencas.json"
    assert resumen_file.exists(), "sernageomin_relaves_resumen_cuencas.json debe existir."

    with open(resumen_file, "r", encoding="utf-8") as f:
        resumen = json.load(f)

    assert len(resumen) >= 30, f"Se esperaban al menos 30 cuencas con relaves mineros, encontradas {len(resumen)}"

    for c in resumen:
        assert c["total_relaves"] >= 1
        assert c["volumen_total_actual_m3"] >= 0


def test_knowledge_graph_mining_risk_context():
    """Valida la presencia de nodos DepositoRelave y aristas AMENAZA_CUENCA en el grafo."""
    kg_file = DATA_DIR / "knowledge_graph_chile.json"
    assert kg_file.exists(), "knowledge_graph_chile.json debe existir."

    with open(kg_file, "r", encoding="utf-8") as f:
        kg = json.load(f)

    nodes = kg.get("nodes", [])
    edges = kg.get("edges", [])

    relave_nodes = [n for n in nodes if n.get("label") == "DepositoRelave"]
    assert len(relave_nodes) >= 800, f"Se esperaban al menos 800 nodos DepositoRelave, encontrados {len(relave_nodes)}"
    assert all(n.get("bounded_context") == "mining_risk" for n in relave_nodes)

    amenaza_edges = [e for e in edges if e.get("relation_type") == "AMENAZA_CUENCA"]
    assert len(amenaza_edges) >= 700, f"Se esperaban al menos 700 aristas AMENAZA_CUENCA, encontradas {len(amenaza_edges)}"


def test_api_relaves_resumen_cuencas():
    """Valida el endpoint GET /api/relaves/resumen-cuencas."""
    response = client.get("/api/relaves/resumen-cuencas")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 30

    first_cuenca = data[0]["cuenca_codigo"]
    res_single = client.get(f"/api/relaves/resumen-cuencas?cuenca={first_cuenca}")
    assert res_single.status_code == 200
    assert len(res_single.json()) == 1


def test_api_relaves_listing():
    """Valida el endpoint GET /api/relaves/depositos con filtros."""
    response = client.get("/api/relaves/depositos?limit=10")
    assert response.status_code == 200
    res = response.json()
    assert "total_coincidentes" in res
    assert len(res["relaves"]) == 10

    # Filtro por estado abandonado
    res_aband = client.get("/api/relaves/depositos?estado=ABANDONADO")
    assert res_aband.status_code == 200
    aband_data = res_aband.json()
    assert aband_data["total_coincidentes"] >= 400
    for r in aband_data["relaves"]:
        assert r["estado_operativo"] == "ABANDONADO"


def test_api_relave_detail():
    """Valida el endpoint GET /api/relaves/deposito/{id_o_codigo} y error 404."""
    list_res = client.get("/api/relaves/depositos?limit=1")
    relave = list_res.json()["relaves"][0]
    rid = relave["id"]

    res_ok = client.get(f"/api/relaves/deposito/{rid}")
    assert res_ok.status_code == 200
    detail = res_ok.json()
    assert detail["id"] == rid
    assert "clasificacion_riesgo" in detail

    # 404
    res_404 = client.get("/api/relaves/deposito/relave_inexistente_99999")
    assert res_404.status_code == 404
