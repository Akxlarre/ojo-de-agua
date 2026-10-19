"""
Unit and Integration Tests for ACADES / MOP Plantas Desalinizadoras.
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.server import app

client = TestClient(app)
DATA_DIR = Path(__file__).parent.parent / "data"


def test_desaladoras_data_files_exist():
    desal_file = DATA_DIR / "desaladoras_chile.json"
    resumen_file = DATA_DIR / "desaladoras_resumen_cuencas.json"

    assert desal_file.exists(), "El catastro de desaladoras debe existir."
    assert resumen_file.exists(), "El resumen por cuencas debe existir."

    with open(desal_file, "r", encoding="utf-8") as f:
        plantas = json.load(f)
        assert len(plantas) >= 50, f"Debe haber al menos 50 plantas desalinizadoras, hay {len(plantas)}"
        primera = plantas[0]
        assert "capacidad_lps" in primera
        assert "capacidad_m3_dia" in primera
        assert "sector_destino" in primera
        assert "es_operativa" in primera
        assert "cuenca_codigo" in primera


def test_api_desaladoras_resumen_cuencas():
    response = client.get("/api/desaladoras/resumen-cuencas")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 15

    # Filtrar por cuenca 023 (Antofagasta / Loa-Carrizalillo)
    resp_cuenca = client.get("/api/desaladoras/resumen-cuencas?cuenca=023")
    assert resp_cuenca.status_code == 200
    data_cuenca = resp_cuenca.json()
    assert len(data_cuenca) == 1
    assert data_cuenca[0]["cuenca_codigo"] == "023"
    assert data_cuenca[0]["capacidad_operacion_lps"] > 1000.0


def test_api_desaladoras_plantas():
    response = client.get("/api/desaladoras/plantas?limit=10")
    assert response.status_code == 200
    res = response.json()
    assert "total_coincidentes" in res
    assert "plantas_desalinizadoras" in res
    assert len(res["plantas_desalinizadoras"]) <= 10
    assert res["total_coincidentes"] >= 50

    # Filtro por operativa
    resp_op = client.get("/api/desaladoras/plantas?operativa_solo=true")
    assert resp_op.status_code == 200
    res_op = resp_op.json()
    for p in res_op["plantas_desalinizadoras"]:
        assert p["es_operativa"] is True


def test_api_desaladoras_planta_detalle():
    # Obtener listado y tomar el id de la primera
    list_resp = client.get("/api/desaladoras/plantas?limit=1")
    assert list_resp.status_code == 200
    primera_id = list_resp.json()["plantas_desalinizadoras"][0]["id"]

    resp = client.get(f"/api/desaladoras/planta/{primera_id}")
    assert resp.status_code == 200
    planta = resp.json()
    assert planta["id"] == primera_id
    assert "nombre" in planta
    assert "operador" in planta


def test_api_desaladoras_planta_no_encontrada():
    resp = client.get("/api/desaladoras/planta/inexistente-12345")
    assert resp.status_code == 404
