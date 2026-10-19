"""
Unit tests for TGR Patentes por No Uso de Aguas dataset and API endpoints.
"""

import json
from pathlib import Path
from starlette.testclient import TestClient
from src.api.server import app

client = TestClient(app)


def test_tgr_patentes_dataset_integrity():
    data_path = Path(__file__).parent.parent / "data" / "patentes_no_uso_chile.json"
    assert data_path.exists(), "patentes_no_uso_chile.json must exist"
    
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert data["total_registros_patentes"] >= 40000
    assert data["total_titulares_unicos"] >= 4000
    assert data["deuda_pendiente_clp"] > 500_000_000_000 # More than 500,000 million CLP
    assert data["total_utm_liquidadas"] > 10_000_000 # More than 10 million UTM
    
    # Check that juridica has more debt than natural (structural hoarding pattern)
    juridica_deuda = data["desglose_por_tipo"]["juridica"]["deuda_clp"]
    natural_deuda = data["desglose_por_tipo"]["natural"]["deuda_clp"]
    assert juridica_deuda > natural_deuda


def test_api_patentes_no_uso_general():
    response = client.get("/api/patentes-no-uso")
    assert response.status_code == 200
    data = response.json()
    assert "total_registros_patentes" in data
    assert "ranking_comunas_top_25" in data
    assert len(data["ranking_titulares_top_50"]) == 50


def test_api_patentes_no_uso_filtro_comuna():
    response = client.get("/api/patentes-no-uso?comuna=Linares")
    assert response.status_code == 200
    data = response.json()
    assert data["filtro_comuna"] == "Linares"
    assert len(data["metricas_comuna"]) > 0
    assert any("LINARES" in c["comuna"] for c in data["metricas_comuna"])
