"""
Unit and Integration Tests for SMA Environmental Sanctions Integration.
Verifies data normalization, cuenca assignment, graph entities, and FastAPI REST endpoints.
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.server import app

client = TestClient(app)
DATA_DIR = Path(__file__).parent.parent / "data"


def test_sma_sanciones_json_integrity():
    """Valida la integridad y completitud del dataset normalizado de sanciones SMA."""
    sanciones_file = DATA_DIR / "sma_sanciones_agua_chile.json"
    assert sanciones_file.exists(), "El archivo de sanciones SMA normalizado debe existir."

    with open(sanciones_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert len(data) >= 3500, f"Se esperaban al menos 3,500 sanciones SMA, se encontraron {len(data)}"

    # Verificar estructura del primer registro
    sample = data[0]
    required_keys = [
        "id", "proceso_sancion_id", "expediente", "tipo_procedimiento",
        "estado", "multa_total_uta", "unidad_fiscalizable_id",
        "unidad_fiscalizable_nombre", "categoria_economica", "cuenca_codigo",
        "cuenca_nombre", "es_relevante_agua", "link_snifa"
    ]
    for key in required_keys:
        assert key in sample, f"Clave requerida '{key}' no encontrada en registro de sanción."

    # Verificar que existen sanciones de relevancia hídrica
    agua_count = sum(1 for s in data if s.get("es_relevante_agua"))
    assert agua_count >= 1000, f"Deberían existir al menos 1,000 sanciones hídrico-sensibles, encontradas {agua_count}"


def test_sma_resumen_cuencas_integrity():
    """Valida la síntesis territorial de infracciones ambientales por macrocuenca."""
    resumen_file = DATA_DIR / "sma_resumen_cuencas.json"
    assert resumen_file.exists(), "El archivo de resumen por cuencas debe existir."

    with open(resumen_file, "r", encoding="utf-8") as f:
        resumen = json.load(f)

    assert len(resumen) >= 50, f"Se esperaban al menos 50 cuencas con sanciones, se encontraron {len(resumen)}"

    # Cuenca Río Maipo (057) debe estar presente y con alta cantidad de sanciones
    maipo = next((c for c in resumen if c["cuenca_codigo"] == "057"), None)
    assert maipo is not None, "La Cuenca del Río Maipo (057) debe estar en el resumen SMA."
    assert maipo["total_sanciones"] >= 500, "Cuenca Maipo debería tener más de 500 procesos históricos."
    assert maipo["total_multa_uta"] > 10000, "Cuenca Maipo debe acumular más de 10,000 UTA en multas."


def test_knowledge_graph_sma_nodes():
    """Valida la presencia de nodos y relaciones de la SMA en el grafo de conocimiento semántico."""
    kg_file = DATA_DIR / "knowledge_graph_chile.json"
    assert kg_file.exists(), "El grafo de conocimiento debe existir."

    with open(kg_file, "r", encoding="utf-8") as f:
        kg = json.load(f)

    nodes = kg.get("nodes", [])
    edges = kg.get("edges", [])

    sma_nodes = [n for n in nodes if n.get("label") == "SancionAmbiental"]
    assert len(sma_nodes) >= 1000, f"Se esperaban al menos 1,000 nodos SancionAmbiental, encontrados {len(sma_nodes)}"

    # Verificar bounded context
    assert all(n.get("bounded_context") == "environmental_compliance" for n in sma_nodes)

    # Verificar aristas INFRINGE_EN_CUENCA
    infringe_edges = [e for e in edges if e.get("relation_type") == "INFRINGE_EN_CUENCA"]
    assert len(infringe_edges) >= 1000, f"Se esperaban al menos 1,000 aristas INFRINGE_EN_CUENCA, encontradas {len(infringe_edges)}"


def test_api_sma_sanciones_endpoint():
    """Valida el endpoint REST GET /api/sma/sanciones con filtros de cuenca y relevancia hídrica."""
    resp = client.get("/api/sma/sanciones?cuenca=057&limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_coincidentes"] > 0
    assert len(data["sanciones"]) <= 10
    assert all(s["cuenca_codigo"] == "057" for s in data["sanciones"])

    # Filtro solo_agua
    resp_agua = client.get("/api/sma/sanciones?cuenca=057&solo_agua=true&limit=10")
    assert resp_agua.status_code == 200
    data_agua = resp_agua.json()
    assert all(s["es_relevante_agua"] is True for s in data_agua["sanciones"])


def test_api_sma_resumen_cuencas_endpoint():
    """Valida el endpoint REST GET /api/sma/resumen-cuencas."""
    resp = client.get("/api/sma/resumen-cuencas?cuenca=034")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    cuenca_huasco = data[0]
    assert cuenca_huasco["cuenca_codigo"] == "034"
    assert "casos_destacados" in cuenca_huasco


def test_api_sma_sancion_detail_and_404():
    """Valida el endpoint de detalle de un expediente específico y manejo de 404."""
    # Sanción id 1 (Pascua Lama)
    resp = client.get("/api/sma/sancion/1")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["proceso_sancion_id"] == "1"
    assert "BARRICK - PASCUA LAMA" in detail["unidad_fiscalizable_nombre"]
    assert detail["multa_total_uta"] > 5000.0

    # 404 Not Found
    resp_404 = client.get("/api/sma/sancion/inexistente_999999")
    assert resp_404.status_code == 404
