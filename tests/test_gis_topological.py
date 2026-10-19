"""
Unit tests for GIS models, Topological Guardrails, and Basin Ingestion.
"""

import pytest
from src.domain.physical.gis import CoordenadaWGS84, CuencaHidrograficaDGA, GeoBoundingBox
from src.guardrails.topological_guard import TopologicalGuardrail
from src.harness.gis_ingestor import ChileGISBasinIngestor
from src.harness.runner import KnowledgeHarness


def test_cuenca_gis_containment():
    # Cuenca Río Maipo bbox: lat [-34.0, -33.0], lon [-71.8, -69.8]
    bbox_maipo = GeoBoundingBox(lat_min=-34.0, lat_max=-33.0, lon_min=-71.8, lon_max=-69.8)
    cuenca_maipo = CuencaHidrograficaDGA(
        codigo_dga="057",
        nombre="Cuenca del Río Maipo",
        region="Metropolitana",
        zona_hidrografica="Zona Central",
        superficie_km2=15380.0,
        bbox=bbox_maipo
    )

    # Santiago / San José de Maipo point: lat -33.6, lon -70.3 -> INSIDE
    coord_inside = CoordenadaWGS84(latitud=-33.6, longitud=-70.3)
    assert cuenca_maipo.contiene_punto(coord_inside) is True

    # Antofagasta point: lat -23.6, lon -70.4 -> OUTSIDE
    coord_outside = CoordenadaWGS84(latitud=-23.6, longitud=-70.4)
    assert cuenca_maipo.contiene_punto(coord_outside) is False


def test_topological_guardrail_spatial_containment():
    bbox_maipo = GeoBoundingBox(lat_min=-34.0, lat_max=-33.0, lon_min=-71.8, lon_max=-69.8)
    cuenca_maipo = CuencaHidrograficaDGA(
        codigo_dga="057",
        nombre="Cuenca del Río Maipo",
        region="Metropolitana",
        zona_hidrografica="Zona Central",
        superficie_km2=15380.0,
        bbox=bbox_maipo
    )

    # Illegal coordinate: trying to place a bocatoma in Biobío (-37.5) under Cuenca Maipo
    coord_erronea = CoordenadaWGS84(latitud=-37.5, longitud=-72.5)
    res = TopologicalGuardrail.validate_spatial_containment(
        coordenada=coord_erronea,
        cuenca=cuenca_maipo,
        nombre_elemento="Bocatoma Falsa"
    )

    assert res.is_valid is False
    assert len(res.violations) == 1
    assert "GUARD-TOPOLOGY-001" in res.violations[0]


def test_topological_guardrail_gravity_flow():
    # Point of intake: 850 msnm. Point of delivery: 920 msnm (water running uphill without pump!)
    res = TopologicalGuardrail.validate_gravity_flow(
        cota_captacion_msnm=850.0,
        cota_entrega_msnm=920.0,
        tiene_estacion_bombeo=False,
        nombre_canal="Canal Imposible"
    )
    assert res.is_valid is False
    assert len(res.violations) == 1
    assert "GUARD-PHYSICS-002" in res.violations[0]

    # With certified pumping station -> allowed
    res_pump = TopologicalGuardrail.validate_gravity_flow(
        cota_captacion_msnm=850.0,
        cota_entrega_msnm=920.0,
        tiene_estacion_bombeo=True,
        nombre_canal="Canal con Bombeo Elevador"
    )
    assert res_pump.is_valid is True


def test_chile_gis_basin_ingestion():
    harness = KnowledgeHarness()
    ingestor = ChileGISBasinIngestor(harness)
    report = ingestor.load_and_ingest()

    assert report.success is True
    assert report.nodes_added >= 20 # 20 key basins + multiple rivers and JVs
    assert report.edges_added >= 20

    # Query for "Río Biobío" through harness
    ctx = harness.prepare_agent_context("¿Qué cuenca y ríos pertenecen al Biobío?")
    assert len(ctx["relevant_graph_nodes"]) > 0
    node_names = [n["name"] for n in ctx["relevant_graph_nodes"]]
    assert any("Biobío" in name for name in node_names)
