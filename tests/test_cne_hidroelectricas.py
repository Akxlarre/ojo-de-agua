"""
Unit and Integration Tests for CNE Centrales Hidroeléctricas en Operación.
Verifies hydroelectric generation normalization, basin power balances, graph nodes, and FastAPI REST endpoints.
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.server import app

client = TestClient(app)
DATA_DIR = Path(__file__).parent.parent / "data"


def test_cne_centrales_integrity():
    """Valida la integridad del dataset de centrales hidroeléctricas CNE."""
    centrales_file = DATA_DIR / "cne_hidroelectricas_chile.json"
    assert centrales_file.exists(), "cne_hidroelectricas_chile.json debe existir."

    with open(centrales_file, "r", encoding="utf-8") as f:
        centrales = json.load(f)

    assert len(centrales) >= 180, f"Se esperaban al menos 180 centrales hidroeléctricas, encontradas {len(centrales)}"

    sample = centrales[0]
    required_keys = [
        "id", "id_ge_hidro", "nombre", "propietario", "tipo_tecnologia",
        "potencia_mw", "unidades_generacion", "sistema_electrico", "cuenca_codigo", "cuenca_nombre"
    ]
    for k in required_keys:
        assert k in sample, f"Clave requerida '{k}' no encontrada en central hidroeléctrica."

    assert sample["potencia_mw"] > 0, "La potencia instalada debe ser mayor a 0 MW."
    assert sample["tipo_tecnologia"] in ["Pasada", "Embalse"], "Tecnología debe ser Pasada o Embalse."


def test_cne_resumen_cuencas_integrity():
    """Valida el balance hidroeléctrico agregado por macrocuenca."""
    resumen_file = DATA_DIR / "cne_hidro_resumen_cuencas.json"
    assert resumen_file.exists(), "cne_hidro_resumen_cuencas.json debe existir."

    with open(resumen_file, "r", encoding="utf-8") as f:
        resumen = json.load(f)

    assert len(resumen) >= 20, f"Se esperaban al menos 20 cuencas con generación hidroeléctrica, encontradas {len(resumen)}"

    # Verificar que esté ordenado por potencia descendente
    mw_list = [c["potencia_total_mw"] for c in resumen]
    assert mw_list == sorted(mw_list, reverse=True), "Las cuencas deben estar ordenadas por potencia decreciente."

    # Top cuenca hidroeléctrica (Biobío o Maule) debe tener más de 1,000 MW
    top_cuenca = resumen[0]
    assert top_cuenca["potencia_total_mw"] >= 1000.0, f"La cuenca líder debe superar 1,000 MW, encontrada {top_cuenca['cuenca_nombre']} con {top_cuenca['potencia_total_mw']} MW"


def test_knowledge_graph_energy_context():
    """Valida la presencia de nodos CentralHidroelectrica y aristas TURBINA_EN_CUENCA en el grafo."""
    kg_file = DATA_DIR / "knowledge_graph_chile.json"
    assert kg_file.exists(), "knowledge_graph_chile.json debe existir."

    with open(kg_file, "r", encoding="utf-8") as f:
        kg = json.load(f)

    nodes = kg.get("nodes", [])
    edges = kg.get("edges", [])

    hidro_nodes = [n for n in nodes if n.get("label") == "CentralHidroelectrica"]
    assert len(hidro_nodes) >= 180, f"Se esperaban al menos 180 nodos CentralHidroelectrica, encontrados {len(hidro_nodes)}"
    assert all(n.get("bounded_context") == "energy" for n in hidro_nodes)

    turbina_edges = [e for e in edges if e.get("relation_type") == "TURBINA_EN_CUENCA"]
    assert len(turbina_edges) >= 180, f"Se esperaban al menos 180 aristas TURBINA_EN_CUENCA, encontradas {len(turbina_edges)}"


def test_api_cne_resumen_cuencas():
    """Valida el endpoint GET /api/cne/resumen-cuencas."""
    response = client.get("/api/cne/resumen-cuencas")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 20

    top_cod = data[0]["cuenca_codigo"]
    res_single = client.get(f"/api/cne/resumen-cuencas?cuenca={top_cod}")
    assert res_single.status_code == 200
    assert len(res_single.json()) == 1


def test_api_cne_hidroelectricas_listing():
    """Valida el endpoint GET /api/cne/hidroelectricas con filtros."""
    response = client.get("/api/cne/hidroelectricas?limit=10")
    assert response.status_code == 200
    res = response.json()
    assert "total_coincidentes" in res
    assert len(res["centrales"]) == 10

    # Filtro por tecnología Embalse y potencia mínima
    res_emb = client.get("/api/cne/hidroelectricas?tecnologia=Embalse&min_mw=50")
    assert res_emb.status_code == 200
    emb_data = res_emb.json()
    assert emb_data["total_coincidentes"] >= 5
    for c in emb_data["centrales"]:
        assert c["tipo_tecnologia"] == "Embalse"
        assert c["potencia_mw"] >= 50.0


def test_api_cne_central_detail():
    """Valida el endpoint GET /api/cne/central/{id_o_nombre} y error 404."""
    list_res = client.get("/api/cne/hidroelectricas?limit=1")
    central = list_res.json()["centrales"][0]
    cid = central["id"]

    res_ok = client.get(f"/api/cne/central/{cid}")
    assert res_ok.status_code == 200
    detail = res_ok.json()
    assert detail["id"] == cid
    assert "potencia_mw" in detail

    # 404
    res_404 = client.get("/api/cne/central/central_inexistente_99999")
    assert res_404.status_code == 404
