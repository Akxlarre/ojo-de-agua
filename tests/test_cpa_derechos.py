"""
Unit and Integration Tests for DGA Catastro Público de Aguas (CPA / DAA).
Verifies water rights normalization, basin volumetric balance, graph nodes, and FastAPI REST endpoints.
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.server import app

client = TestClient(app)
DATA_DIR = Path(__file__).parent.parent / "data"


def test_cpa_resumen_cuencas_integrity():
    """Valida la integridad del resumen de derechos de agua por macrocuenca."""
    resumen_file = DATA_DIR / "cpa_resumen_cuencas.json"
    assert resumen_file.exists(), "cpa_resumen_cuencas.json debe existir."

    with open(resumen_file, "r", encoding="utf-8") as f:
        resumen = json.load(f)

    assert len(resumen) >= 70, f"Se esperaban al menos 70 cuencas con derechos de agua, obtenidas {len(resumen)}"

    # Verificar Cuenca del Río Maipo (057)
    maipo = next((c for c in resumen if c["cuenca_codigo"] == "057"), None)
    assert maipo is not None, "Cuenca Maipo (057) debe estar presente en el balance CPA."
    assert maipo["total_derechos"] >= 10000, f"Cuenca Maipo debería registrar más de 10,000 derechos, encontrados {maipo['total_derechos']}"
    assert maipo["derechos_consuntivos"] > 10000
    assert maipo["caudal_consuntivo_total_lps"] > 1000000
    assert len(maipo["principales_titulares"]) >= 1
    assert len(maipo["titulos_destacados"]) >= 1


def test_cpa_derechos_destacados_integrity():
    """Valida el dataset de derechos estratégicos extraídos para el grafo."""
    destacados_file = DATA_DIR / "cpa_derechos_destacados.json"
    assert destacados_file.exists(), "cpa_derechos_destacados.json debe existir."

    with open(destacados_file, "r", encoding="utf-8") as f:
        destacados = json.load(f)

    assert len(destacados) >= 5000, f"Se esperaban al menos 5,000 derechos estratégicos, obtenidos {len(destacados)}"

    sample = destacados[0]
    required_keys = [
        "id", "codigo_expediente", "titular", "tipo_derecho",
        "naturaleza_agua", "ejercicio_derecho", "caudal_concedido_lps",
        "cuenca_codigo", "cuenca_nombre"
    ]
    for k in required_keys:
        assert k in sample, f"Clave requerida '{k}' no encontrada en derecho de agua."

    assert sample["caudal_concedido_lps"] > 0, "El caudal otorgado debe ser estrictamente positivo."


def test_knowledge_graph_water_rights_context():
    """Valida la presencia de nodos de derechos de aprovechamiento y aristas de concesión en el grafo semántico."""
    kg_file = DATA_DIR / "knowledge_graph_chile.json"
    assert kg_file.exists(), "knowledge_graph_chile.json debe existir."

    with open(kg_file, "r", encoding="utf-8") as f:
        kg = json.load(f)

    nodes = kg.get("nodes", [])
    edges = kg.get("edges", [])

    daa_nodes = [n for n in nodes if n.get("label") == "DerechoAprovechamiento"]
    assert len(daa_nodes) >= 3500, f"Se esperaban al menos 3,500 nodos DerechoAprovechamiento, encontrados {len(daa_nodes)}"

    # Verificar bounded context
    assert all(n.get("bounded_context") == "water_rights" for n in daa_nodes)

    # Verificar aristas CONCEDIDO_EN_CUENCA
    concedido_edges = [e for e in edges if e.get("relation_type") == "CONCEDIDO_EN_CUENCA"]
    assert len(concedido_edges) >= 3500, f"Se esperaban al menos 3,500 aristas CONCEDIDO_EN_CUENCA, encontradas {len(concedido_edges)}"


def test_api_cpa_resumen_cuencas_endpoint():
    """Valida el endpoint REST GET /api/cpa/resumen-cuencas."""
    resp = client.get("/api/cpa/resumen-cuencas?cuenca=057")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    cuenca_maipo = data[0]
    assert cuenca_maipo["cuenca_codigo"] == "057"
    assert "caudal_consuntivo_total_lps" in cuenca_maipo
    assert "derechos_consuntivos" in cuenca_maipo


def test_api_cpa_derechos_endpoint():
    """Valida el endpoint REST GET /api/cpa/derechos con filtros paramétricos."""
    resp = client.get("/api/cpa/derechos?cuenca=057&tipo=Consuntivo&limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_coincidentes"] > 0
    assert len(data["derechos"]) <= 10
    assert all(d["cuenca_codigo"] == "057" for d in data["derechos"])
    assert all("consuntivo" in d["tipo_derecho"].lower() for d in data["derechos"])


def test_api_cpa_derecho_detail_and_404():
    """Valida la obtención de un derecho específico por expediente y respuesta 404."""
    # Obtener un derecho real de la lista
    resp_list = client.get("/api/cpa/derechos?limit=1")
    assert resp_list.status_code == 200
    first = resp_list.json()["derechos"][0]
    exp = first["codigo_expediente"]

    # Consultar detalle
    resp_det = client.get(f"/api/cpa/derecho/{exp}")
    assert resp_det.status_code == 200
    detail = resp_det.json()
    assert detail["codigo_expediente"] == exp
    assert detail["titular"] == first["titular"]

    # 404
    resp_404 = client.get("/api/cpa/derecho/EXPEDIENTE_FANTASMA_999999")
    assert resp_404.status_code == 404
