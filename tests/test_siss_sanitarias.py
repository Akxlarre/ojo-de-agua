"""
Unit and Integration Tests for SISS Plantas de Tratamiento de Aguas Servidas (PTAS).
Verifies PTAS normalization, basin discharge balance, graph nodes, and FastAPI REST endpoints.
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.server import app

client = TestClient(app)
DATA_DIR = Path(__file__).parent.parent / "data"


def test_siss_plantas_integrity():
    """Valida la integridad del dataset normalizado de plantas de tratamiento SISS."""
    plantas_file = DATA_DIR / "siss_plantas_chile.json"
    assert plantas_file.exists(), "siss_plantas_chile.json debe existir."

    with open(plantas_file, "r", encoding="utf-8") as f:
        plantas = json.load(f)

    assert len(plantas) >= 250, f"Se esperaban al menos 250 plantas PTAS, encontradas {len(plantas)}"

    sample = plantas[0]
    required_keys = [
        "id", "codigo_obra", "nombre", "empresa_concesionaria",
        "cuerpo_receptor", "tipo_receptor", "cuenca_codigo", "cuenca_nombre"
    ]
    for k in required_keys:
        assert k in sample, f"Clave requerida '{k}' no encontrada en planta PTAS."

    assert sample["coordenadas"] is not None, "Las plantas deben contar con coordenadas geográficas."


def test_siss_resumen_cuencas_integrity():
    """Valida la agregación de descargas sanitarias por macrocuenca receptora."""
    resumen_file = DATA_DIR / "siss_resumen_cuencas.json"
    assert resumen_file.exists(), "siss_resumen_cuencas.json debe existir."

    with open(resumen_file, "r", encoding="utf-8") as f:
        resumen = json.load(f)

    assert len(resumen) >= 30, f"Se esperaban al menos 30 cuencas receptoras de PTAS, encontradas {len(resumen)}"

    # Verificar presencia de la Cuenca del Río Maipo (057)
    maipo = next((c for c in resumen if c["cuenca_codigo"] == "057"), None)
    assert maipo is not None, "Cuenca Maipo (057) debe registrar descargas PTAS."
    assert maipo["total_plantas"] >= 10, f"Cuenca Maipo debería tener >= 10 PTAS, encontradas {maipo['total_plantas']}"
    assert any("aguas" in e.lower() for e in maipo["empresas_sanitarias"])


def test_knowledge_graph_sanitation_context():
    """Valida la presencia de nodos PlantaTratamiento y aristas DESCARGA_EN_CUENCA en el grafo."""
    kg_file = DATA_DIR / "knowledge_graph_chile.json"
    assert kg_file.exists(), "knowledge_graph_chile.json debe existir."

    with open(kg_file, "r", encoding="utf-8") as f:
        kg = json.load(f)

    nodes = kg.get("nodes", [])
    edges = kg.get("edges", [])

    ptas_nodes = [n for n in nodes if n.get("label") == "PlantaTratamiento"]
    assert len(ptas_nodes) >= 150, f"Se esperaban al menos 150 nodos PlantaTratamiento, encontrados {len(ptas_nodes)}"
    assert all(n.get("bounded_context") == "sanitation" for n in ptas_nodes)

    descarga_edges = [e for e in edges if e.get("relation_type") == "DESCARGA_EN_CUENCA"]
    assert len(descarga_edges) >= 150, f"Se esperaban al menos 150 aristas DESCARGA_EN_CUENCA, encontradas {len(descarga_edges)}"


def test_api_siss_resumen_cuencas():
    """Valida el endpoint GET /api/siss/resumen-cuencas y su filtro por cuenca."""
    response = client.get("/api/siss/resumen-cuencas")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 30

    # Filtro por cuenca Maipo
    res_maipo = client.get("/api/siss/resumen-cuencas?cuenca=057")
    assert res_maipo.status_code == 200
    data_maipo = res_maipo.json()
    assert len(data_maipo) == 1
    assert data_maipo[0]["cuenca_codigo"] == "057"


def test_api_siss_plantas_listing():
    """Valida el endpoint GET /api/siss/plantas con paginación y filtros."""
    response = client.get("/api/siss/plantas?limit=10")
    assert response.status_code == 200
    res = response.json()
    assert "total_coincidentes" in res
    assert len(res["plantas"]) == 10

    # Filtro por tipo de cuerpo receptor
    res_cauce = client.get("/api/siss/plantas?tipo_receptor=Cauce Natural")
    assert res_cauce.status_code == 200
    cauce_data = res_cauce.json()
    assert cauce_data["total_coincidentes"] > 0
    assert all("cauce" in p["categoria_receptor"].lower() or "cauce" in p["tipo_receptor"].lower() for p in cauce_data["plantas"])


def test_api_siss_planta_detail():
    """Valida el endpoint GET /api/siss/planta/{id_o_codigo} con casos válidos y 404."""
    # Buscar una planta existente
    list_res = client.get("/api/siss/plantas?limit=1")
    planta = list_res.json()["plantas"][0]
    pid = planta["id"]

    res_ok = client.get(f"/api/siss/planta/{pid}")
    assert res_ok.status_code == 200
    detail = res_ok.json()
    assert detail["id"] == pid
    assert "empresa_concesionaria" in detail

    # Caso 404
    res_404 = client.get("/api/siss/planta/planta_inexistente_99999")
    assert res_404.status_code == 404
