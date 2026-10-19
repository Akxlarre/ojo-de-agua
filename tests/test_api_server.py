"""
Unit and integration tests for the FastAPI Chilean Water Governance Server.
"""

import pytest
from starlette.testclient import TestClient
from src.api.server import app

client = TestClient(app)


def test_api_index_status():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["grafo_conocimiento"]["total_nodos"] >= 400
    assert data["grafo_conocimiento"]["cuencas_oficiales"] >= 80


def test_api_mapa_html():
    response = client.get("/mapa")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "leaflet" in response.text
    assert "Red Hídrica Nacional" in response.text


def test_api_listar_cuencas_filtro_region():
    response = client.get("/api/cuencas?region=Metropolitana")
    assert response.status_code == 200
    cuencas = response.json()
    assert len(cuencas) > 0
    names = [c["nombre"] for c in cuencas]
    assert any("Maipo" in n for n in names)


def test_api_listar_ouas_filtro_cuenca():
    response = client.get("/api/ouas?cuenca=054") # Aconcagua
    assert response.status_code == 200
    ouas = response.json()
    assert len(ouas) > 0
    names = [o["nombre"] for o in ouas]
    assert any("Aconcagua" in n for n in names)


def test_api_prorrateo_simulacion():
    payload = {
        "caudal_afluente_lps": 5000.0,
        "caudal_ecologico_minimo_lps": 1000.0,
        "demandas_canales": [
            {
                "bocatoma_id": "boc-san-carlos",
                "nombre_canal": "Canal San Carlos",
                "caudal_consumo_humano_lps": 1000.0,
                "caudal_permanente_autorizado_lps": 6000.0,
                "caudal_eventual_autorizado_lps": 2000.0
            }
        ]
    }
    response = client.post("/api/prorrateo", json=payload)
    assert response.status_code == 200
    data = response.json()
    # 5,000 - 1,000 (humano) - 1,000 (ecológico) = 3,000 L/s remanente para 6,000 permanente -> alpha = 0.50
    assert data["factor_prorrateo_permanente"] == 0.50
    assert data["factor_prorrateo_eventual"] == 0.0
    assert data["estado_cuenca"] == "Prorrateo Severo (Factor Permanente <= 0.70)"


def test_api_auditoria_extraccion_clandestina():
    payload = {
        "lectura_mee": {
            "bocatoma_id": "boc-clandestina",
            "sensor_id": "mee-099",
            "caudal_instantaneo_lps": 250.0
        },
        "ordenes_activas": []
    }
    response = client.post("/api/auditoria/extraccion", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["infraccion_detectada"] is True
    assert data["alerta"]["tipo_infraccion"] == "EXTRACCION_CLANDESTINA_SIN_TURNO"


def test_api_consulta_con_acl_sanitizacion():
    payload = {
        "consulta": "¿Quién opera el comite de rio en la cuenca del Río Huasco?",
        "contexto_delimitado": "OUA"
    }
    response = client.post("/api/consulta", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Debe haber reemplazado 'comite de rio' por 'Junta de Vigilancia'
    assert "Junta de Vigilancia" in data["consulta_sanitizada_acl"]
    assert "comite de rio" not in data["consulta_sanitizada_acl"]
    assert data["total_encontrados"] > 0


def test_api_listar_shac():
    response = client.get("/api/shac?region=Atacama")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert "codigo_shac" in data[0]
    assert "area_km2" in data[0]


def test_api_listar_estaciones_bna():
    response = client.get("/api/estaciones-bna?tipo=FLUVIOMETRICA")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert "codigo_bna" in data[0]
    assert "FLUVIOMETRICA" in data[0]["tipo"]


def test_api_listar_decretos_escasez():
    response = client.get("/api/decretos-escasez?vigente=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["es_vigente"] is True
