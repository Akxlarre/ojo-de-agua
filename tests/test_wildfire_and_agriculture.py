"""
Unit and Integration Tests for Wildfire Risk (CONAF) and Agricultural Demand (CNR).
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.server import app
from src.domain.analytics.diagnostic_service import HolisticCuencaDiagnosticService
from src.domain.topological.cross_relations import CrossDomainRelationBuilder
from src.harness.dga_catastro_ingestor import DGACatastroIngestor
from src.harness.runner import KnowledgeHarness
from src.memory.graph import DomainEdge, DomainKnowledgeGraph, DomainNode

client = TestClient(app)
DATA_DIR = Path(__file__).parent.parent / "data"


def test_datasets_wildfire_and_agriculture_exist():
    inc_file = DATA_DIR / "conaf_incendios_chile.json"
    inc_cuencas_file = DATA_DIR / "conaf_incendios_resumen_cuencas.json"
    riego_cuencas_file = DATA_DIR / "cnr_demanda_agricola_cuencas.json"
    riego_predios_file = DATA_DIR / "cnr_riego_predios_destacados.json"

    assert inc_file.exists()
    assert inc_cuencas_file.exists()
    assert riego_cuencas_file.exists()
    assert riego_predios_file.exists()

    inc_data = json.loads(inc_file.read_text(encoding="utf-8"))
    assert len(inc_data) >= 10
    assert any(i["nombre"] == "Complejo Las Pataguas - Lago Peñuelas" for i in inc_data)

    riego_cuencas = json.loads(riego_cuencas_file.read_text(encoding="utf-8"))
    assert len(riego_cuencas) == 90
    assert any(c["cuenca_codigo"] == "057" for c in riego_cuencas)

    riego_predios = json.loads(riego_predios_file.read_text(encoding="utf-8"))
    assert len(riego_predios) >= 8


def test_cross_relations_wildfire_and_agriculture():
    graph = DomainKnowledgeGraph()

    # Incendio en cuenca 054
    incendio = DomainNode(
        id="INC-TEST-001",
        label="IncendioForestal",
        name="Incendio Test Peñuelas",
        bounded_context="wildfire_risk",
        properties={
            "cuenca_codigo": "054",
            "superficie_ha": 9400.0,
            "severidad": "EXTREMA",
            "coordenadas": [-33.12, -71.51],
            "impacto_embalse": "Sedimentación directa en Tranque Peñuelas",
            "riesgo_aluvial_post_incendio": "CRÍTICO"
        }
    )
    graph.add_node(incendio)

    # Embalse Peñuelas a menos de 5 km
    embalse = DomainNode(
        id="emb_test_penuelas",
        label="Embalse",
        name="Embalse Peñuelas",
        bounded_context="infrastructure",
        properties={
            "nombre": "EMBALSE PEÑUELAS",
            "cuenca_codigo": "054",
            "coordenadas": [-33.14, -71.53]
        }
    )
    graph.add_node(embalse)

    # Demanda Agrícola crítica en cuenca 057
    demanda = DomainNode(
        id="demanda_agricola_057",
        label="DemandaAgricola",
        name="Demanda Agrícola Maipo",
        bounded_context="agricultural_demand",
        properties={
            "cuenca_codigo": "057",
            "demanda_media_agricola_lps": 45000.0,
            "estres_hidrico_agricola": "CRÍTICO",
            "porcentaje_tecnificacion": 55.0
        }
    )
    graph.add_node(demanda)

    # APR en cuenca 057
    apr = DomainNode(
        id="apr_test_melipilla",
        label="SistemaAPR",
        name="APR Melipilla Rural",
        bounded_context="drinking_water",
        properties={
            "cuenca_codigo": "057",
            "beneficiarios": 2500,
            "coordenadas": [-33.68, -71.21]
        }
    )
    graph.add_node(apr)

    builder = CrossDomainRelationBuilder(graph)
    report = builder.build_all_cross_relations()

    assert report["amenaza_incendio_embalse_added"] >= 1
    assert report["compite_agricola_apr_added"] >= 1

    edges = graph.edges
    amenaza_emb_edges = [e for e in edges if e.relation_type == "AMENAZA_DEGRADACION_CABECERA"]
    assert len(amenaza_emb_edges) == 1
    assert amenaza_emb_edges[0].source_id == "INC-TEST-001"
    assert amenaza_emb_edges[0].target_id == "emb_test_penuelas"
    assert amenaza_emb_edges[0].properties["severidad_incendio"] == "EXTREMA"

    compite_apr_edges = [e for e in edges if e.relation_type == "COMPITE_POR_RECURSO_CON_APR"]
    assert len(compite_apr_edges) == 1
    assert compite_apr_edges[0].source_id == "demanda_agricola_057"
    assert compite_apr_edges[0].target_id == "apr_test_melipilla"


def test_diagnostic_service_with_wildfire_and_riego():
    service = HolisticCuencaDiagnosticService()
    diag = service.calcular_diagnostico_cuenca("057")

    assert diag is not None
    metricas = diag["metricas_clave"]

    # Verificar que las nuevas métricas clave están presentes y pobladas
    assert "incendios_eventos_historicos" in metricas
    assert "incendios_superficie_quemada_ha" in metricas
    assert "demanda_agricola_lps" in metricas
    assert "superficie_regada_ha" in metricas
    assert "tecnificacion_riego_pct" in metricas
    assert "estres_hidrico_agricola" in metricas

    assert metricas["demanda_agricola_lps"] > 0
    assert metricas["superficie_regada_ha"] > 1000


def test_api_incendios_endpoints():
    # 1. Resumen por cuencas
    res_cuencas = client.get("/api/incendios/resumen-cuencas")
    assert res_cuencas.status_code == 200
    data_cuencas = res_cuencas.json()
    assert len(data_cuencas) == 90

    # Filtro por cuenca
    res_filt = client.get("/api/incendios/resumen-cuencas?cuenca=054")
    assert res_filt.status_code == 200
    assert len(res_filt.json()) == 1

    # 2. Listado de eventos
    res_eventos = client.get("/api/incendios/eventos?limit=10")
    assert res_eventos.status_code == 200
    data_ev = res_eventos.json()
    assert "incendios" in data_ev
    assert len(data_ev["incendios"]) >= 1

    # Filtro por severidad
    res_sev = client.get("/api/incendios/eventos?severidad=EXTREMA")
    assert res_sev.status_code == 200
    for inc in res_sev.json()["incendios"]:
        assert inc["severidad"] == "EXTREMA"


def test_api_riego_endpoints():
    # 1. Resumen por cuencas
    res_cuencas = client.get("/api/riego/resumen-cuencas")
    assert res_cuencas.status_code == 200
    data_cuencas = res_cuencas.json()
    assert len(data_cuencas) == 90

    # Filtro por cuenca
    res_filt = client.get("/api/riego/resumen-cuencas?cuenca=073")
    assert res_filt.status_code == 200
    assert len(res_filt.json()) == 1

    # 2. Listado de predios y distritos
    res_predios = client.get("/api/riego/predios")
    assert res_predios.status_code == 200
    data_pred = res_predios.json()
    assert "distritos_riego" in data_pred
    assert len(data_pred["distritos_riego"]) >= 1

    # Filtro por sistema
    res_tec = client.get("/api/riego/predios?sistema_riego=Goteo")
    assert res_tec.status_code == 200
    for p in res_tec.json()["distritos_riego"]:
        assert "goteo" in p["sistema_riego"].lower()
