"""
Unit and Integration Tests for MMA Humedales Urbanos Protegidos (Ley N° 21.202).
Verifies ecosystem conservation normalization, basin wetlands balance, graph nodes, and FastAPI REST endpoints.
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.server import app

client = TestClient(app)
DATA_DIR = Path(__file__).parent.parent / "data"


def test_mma_humedales_integrity():
    """Valida la integridad del dataset de humedales urbanos protegidos del MMA."""
    humedales_file = DATA_DIR / "mma_humedales_chile.json"
    assert humedales_file.exists(), "mma_humedales_chile.json debe existir."

    with open(humedales_file, "r", encoding="utf-8") as f:
        humedales = json.load(f)

    assert len(humedales) >= 100, f"Se esperaban al menos 100 humedales urbanos, encontrados {len(humedales)}"

    sample = humedales[0]
    required_keys = [
        "id", "codigo_humedal", "nombre", "superficie_ha", "superficie_km2",
        "region", "comuna", "resolucion_mma", "cuenca_codigo", "cuenca_nombre", "es_protegido_ley_21202"
    ]
    for k in required_keys:
        assert k in sample, f"Clave requerida '{k}' no encontrada en humedal urbano."

    assert sample["es_protegido_ley_21202"] is True
    assert sample["superficie_ha"] > 0, "La superficie protegida debe ser mayor a 0 ha."


def test_mma_resumen_cuencas_integrity():
    """Valida la agregación de superficie de humedales urbanos por macrocuenca."""
    resumen_file = DATA_DIR / "mma_humedales_resumen_cuencas.json"
    assert resumen_file.exists(), "mma_humedales_resumen_cuencas.json debe existir."

    with open(resumen_file, "r", encoding="utf-8") as f:
        resumen = json.load(f)

    assert len(resumen) >= 20, f"Se esperaban al menos 20 cuencas con humedales urbanos, encontradas {len(resumen)}"

    for c in resumen:
        assert c["total_humedales"] >= 1
        assert c["superficie_protegida_ha"] > 0
        assert len(c["comunas"]) >= 1


def test_knowledge_graph_ecosystems_context():
    """Valida la presencia de nodos HumedalUrbano y aristas PROTEGIDO_EN_CUENCA en el grafo."""
    kg_file = DATA_DIR / "knowledge_graph_chile.json"
    assert kg_file.exists(), "knowledge_graph_chile.json debe existir."

    with open(kg_file, "r", encoding="utf-8") as f:
        kg = json.load(f)

    nodes = kg.get("nodes", [])
    edges = kg.get("edges", [])

    humedal_nodes = [n for n in nodes if n.get("label") == "HumedalUrbano"]
    assert len(humedal_nodes) >= 100, f"Se esperaban al menos 100 nodos HumedalUrbano, encontrados {len(humedal_nodes)}"
    assert all(n.get("bounded_context") == "ecosystems" for n in humedal_nodes)

    protegido_edges = [e for e in edges if e.get("relation_type") == "PROTEGIDO_EN_CUENCA"]
    assert len(protegido_edges) >= 100, f"Se esperaban al menos 100 aristas PROTEGIDO_EN_CUENCA, encontradas {len(protegido_edges)}"


def test_api_mma_resumen_cuencas():
    """Valida el endpoint GET /api/mma/resumen-cuencas."""
    response = client.get("/api/mma/resumen-cuencas")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 20

    first_cuenca = data[0]["cuenca_codigo"]
    res_single = client.get(f"/api/mma/resumen-cuencas?cuenca={first_cuenca}")
    assert res_single.status_code == 200
    assert len(res_single.json()) == 1


def test_api_mma_humedales_listing():
    """Valida el endpoint GET /api/mma/humedales con filtros."""
    response = client.get("/api/mma/humedales?limit=10")
    assert response.status_code == 200
    res = response.json()
    assert "total_coincidentes" in res
    assert len(res["humedales"]) == 10

    # Filtro por nombre
    h0 = res["humedales"][0]
    subname = h0["nombre"].split()[0]
    res_sub = client.get(f"/api/mma/humedales?nombre={subname}")
    assert res_sub.status_code == 200
    assert res_sub.json()["total_coincidentes"] >= 1


def test_api_mma_humedal_detail():
    """Valida el endpoint GET /api/mma/humedal/{codigo_o_id} y error 404."""
    list_res = client.get("/api/mma/humedales?limit=1")
    humedal = list_res.json()["humedales"][0]
    cod = humedal["codigo_humedal"]

    res_ok = client.get(f"/api/mma/humedal/{cod}")
    assert res_ok.status_code == 200
    detail = res_ok.json()
    assert detail["codigo_humedal"] == cod
    assert detail["es_protegido_ley_21202"] is True

    # 404
    res_404 = client.get("/api/mma/humedal/hu-inexistente-99999")
    assert res_404.status_code == 404
