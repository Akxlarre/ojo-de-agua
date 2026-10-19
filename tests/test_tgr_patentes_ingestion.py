"""
Unit and Integration Tests for TGR / DGA Patentes por No Uso de Aguas (Art. 129 bis).
Verifies non-use speculation quantification, basin aggregates, knowledge graph nodes, and FastAPI REST endpoints.
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.server import app

client = TestClient(app)
DATA_DIR = Path(__file__).parent.parent / "data"


def test_tgr_patentes_destacadas_integrity():
    """Valida la integridad de la nómina de patentes por no uso destacadas."""
    patentes_file = DATA_DIR / "tgr_patentes_destacadas.json"
    assert patentes_file.exists(), "tgr_patentes_destacadas.json debe existir."

    with open(patentes_file, "r", encoding="utf-8") as f:
        patentes = json.load(f)

    assert len(patentes) >= 10000, f"Se esperaban al menos 10,000 patentes, encontradas {len(patentes)}"

    sample = patentes[0]
    required_keys = [
        "id", "cuenta_tgr", "rut_rol_titular", "monto_liquidado_clp",
        "saldo_deuda_clp", "utm_liquidada", "ano_patente", "cuenca_codigo"
    ]
    for k in required_keys:
        assert k in sample, f"Clave requerida '{k}' no encontrada en patente por no uso."


def test_tgr_patentes_resumen_cuencas_integrity():
    """Valida la agregación de deudas por no uso de agua por macrocuenca."""
    resumen_file = DATA_DIR / "tgr_patentes_resumen_cuencas.json"
    assert resumen_file.exists(), "tgr_patentes_resumen_cuencas.json debe existir."

    with open(resumen_file, "r", encoding="utf-8") as f:
        resumen = json.load(f)

    assert len(resumen) >= 40, f"Se esperaban al menos 40 cuencas con patentes, encontradas {len(resumen)}"

    for c in resumen:
        assert c["total_patentes_no_uso"] >= 1
        assert c["deuda_total_utm"] >= 0


def test_knowledge_graph_water_rights_enforcement_context():
    """Valida la presencia de nodos PatenteNoUso y aristas AFECTA_DERECHO_EN_CUENCA en el grafo."""
    kg_file = DATA_DIR / "knowledge_graph_chile.json"
    assert kg_file.exists(), "knowledge_graph_chile.json debe existir."

    with open(kg_file, "r", encoding="utf-8") as f:
        kg = json.load(f)

    nodes = kg.get("nodes", [])
    edges = kg.get("edges", [])

    patente_nodes = [n for n in nodes if n.get("label") == "PatenteNoUso"]
    assert len(patente_nodes) >= 15000, f"Se esperaban al menos 15,000 nodos PatenteNoUso, encontrados {len(patente_nodes)}"
    assert all(n.get("bounded_context") == "water_rights_enforcement" for n in patente_nodes)

    afecta_edges = [e for e in edges if e.get("relation_type") == "AFECTA_DERECHO_EN_CUENCA"]
    assert len(afecta_edges) >= 15000, f"Se esperaban al menos 15,000 aristas AFECTA_DERECHO_EN_CUENCA, encontradas {len(afecta_edges)}"


def test_api_patentes_resumen_cuencas():
    """Valida el endpoint GET /api/patentes/resumen-cuencas."""
    response = client.get("/api/patentes/resumen-cuencas")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 40

    first_cuenca = data[0]["cuenca_codigo"]
    res_single = client.get(f"/api/patentes/resumen-cuencas?cuenca={first_cuenca}")
    assert res_single.status_code == 200
    assert len(res_single.json()) == 1


def test_api_patentes_morosos_listing():
    """Valida el endpoint GET /api/patentes/morosos con filtros."""
    response = client.get("/api/patentes/morosos?limit=10")
    assert response.status_code == 200
    res = response.json()
    assert "total_coincidentes" in res
    assert len(res["patentes"]) == 10

    # Filtro por UTM mínima
    res_utm = client.get("/api/patentes/morosos?min_utm=100")
    assert res_utm.status_code == 200
    utm_data = res_utm.json()
    assert utm_data["total_coincidentes"] >= 10
    for p in utm_data["patentes"]:
        assert p["utm_liquidada"] >= 100.0


def test_api_patente_detail():
    """Valida el endpoint GET /api/patentes/patente/{cuenta_o_id} y error 404."""
    list_res = client.get("/api/patentes/morosos?limit=1")
    patente = list_res.json()["patentes"][0]
    pid = patente["id"]

    res_ok = client.get(f"/api/patentes/patente/{pid}")
    assert res_ok.status_code == 200
    detail = res_ok.json()
    assert detail["id"] == pid
    assert "utm_liquidada" in detail

    # 404
    res_404 = client.get("/api/patentes/patente/patente_inexistente_99999")
    assert res_404.status_code == 404
