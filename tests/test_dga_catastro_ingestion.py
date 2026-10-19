"""
Unit test for DGA Open Data Catastro Ingestion (SHACs, Estaciones BNA, Decretos Escasez).
"""

import json
from pathlib import Path
from src.harness.runner import KnowledgeHarness
from src.harness.gis_ingestor import ChileGISBasinIngestor
from src.harness.dga_catastro_ingestor import DGACatastroIngestor


def test_dga_catastro_ingestion_entities_and_relationships():
    harness = KnowledgeHarness()
    
    # Ingest baselines cuencas first
    gis_ingestor = ChileGISBasinIngestor(harness)
    gis_ingestor.load_and_ingest()
    
    # Ingest DGA Catastro
    catastro_ingestor = DGACatastroIngestor(harness)
    rep = catastro_ingestor.load_and_ingest()
    
    # Assertions on entities ingested
    assert rep.shacs_added >= 700, f"Expected at least 700 SHACs, got {rep.shacs_added}"
    assert rep.bna_stations_added >= 3000, f"Expected at least 3000 BNA stations, got {rep.bna_stations_added}"
    assert rep.decrees_added >= 200, f"Expected at least 200 decrees, got {rep.decrees_added}"
    assert rep.prohibitions_added >= 100, f"Expected at least 100 prohibitions, got {rep.prohibitions_added}"
    assert rep.edges_added >= 4000, f"Expected at least 4000 topological/telemetry edges, got {rep.edges_added}"
    
    # Verify node lookup
    shac_nodes = harness.graph.find_nodes_by_label("SHAC")
    assert len(shac_nodes) >= 700
    
    bna_nodes = harness.graph.find_nodes_by_label("EstacionBNA")
    assert len(bna_nodes) >= 3000
    
    # Verify sample properties
    sample_station = bna_nodes[0]
    assert "codigo_bna" in sample_station.properties
    assert "coordenadas" in sample_station.properties
    assert len(sample_station.properties["coordenadas"]) == 2
