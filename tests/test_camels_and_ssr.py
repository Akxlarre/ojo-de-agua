"""
Unit and integration tests for CAMELS-CL and Sistemas Sanitarios Rurales (SSR / APR).
Validates hydroclimatic indicators, Art. 5 bis drinking water coverage, and REST API endpoints.
"""

import json
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from src.api.server import app

client = TestClient(app)
DATA_DIR = Path(__file__).parent.parent / "data"


def test_camels_cl_dataset_integrity():
    camels_file = DATA_DIR / "camels_cl_cuencas.json"
    assert camels_file.exists(), "camels_cl_cuencas.json must exist"

    with open(camels_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert len(data) >= 500, f"Expected at least 500 catchments, got {len(data)}"
    first = data[0]
    assert "codigo_bna" in first
    assert "indice_aridez" in first
    assert "grado_intervencion_antropica" in first
    assert "indices_hidrologicos" in first


def test_sistemas_ssr_apr_dataset_integrity():
    apr_file = DATA_DIR / "sistemas_ssr_apr_chile.json"
    assert apr_file.exists(), "sistemas_ssr_apr_chile.json must exist"

    with open(apr_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert len(data) >= 2000, f"Expected at least 2000 rural drinking water systems, got {len(data)}"
    # Check that header row was stripped
    for s in data:
        assert s["codigo_ssr"] != "N°", "Subheader row should have been filtered out"
        assert "arranques_domiciliarios" in s
        assert "beneficiarios_estimados" in s


def test_api_camels_cl_endpoint():
    resp = client.get("/api/camels-cl")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) > 0
    assert len(items) <= 200

    # Filter by specific BNA code
    first_bna = items[0]["codigo_bna"]
    resp_filtered = client.get(f"/api/camels-cl?codigo_bna={first_bna}")
    assert resp_filtered.status_code == 200
    filtered_items = resp_filtered.json()
    assert len(filtered_items) >= 1
    assert first_bna in filtered_items[0]["codigo_bna"]


def test_api_sistemas_apr_endpoint():
    resp = client.get("/api/sistemas-apr")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) > 0

    # Filter by region
    resp_reg = client.get("/api/sistemas-apr?region=Arica")
    assert resp_reg.status_code == 200
    items_reg = resp_reg.json()
    assert len(items_reg) > 0
    for it in items_reg:
        assert "arica" in it["region"].lower()

    # Filter by comuna
    resp_com = client.get("/api/sistemas-apr?comuna=Arica")
    assert resp_com.status_code == 200
    items_com = resp_com.json()
    assert len(items_com) > 0
