"""
Unit tests for DGA client adapter and automated synchronization hook.
"""

import pytest
from src.domain.legal.dga_client import DGAClientAdapter, DecretoEscasezDGA
from src.harness.dga_hook import DGAAutomationHook
from src.harness.gis_ingestor import ChileGISBasinIngestor
from src.harness.runner import KnowledgeHarness


def test_dga_client_retrieves_gauging_station_telemetry():
    client = DGAClientAdapter()
    lectura = client.get_estacion_lectura("05701001-8")
    
    assert lectura is not None
    assert lectura.estacion_nombre == "Río Maipo en El Manzano"
    assert lectura.caudal_instantaneo_m3s > 0.0
    assert lectura.cuenca_codigo == "057"


from src.harness.oua_national_ingestor import NationalOUAIngestor


def test_dga_hook_syncs_drought_decrees_to_knowledge_graph():
    harness = KnowledgeHarness()
    # Ingest basins and OUAs so JVs exist in the graph
    ChileGISBasinIngestor(harness).load_and_ingest()
    NationalOUAIngestor(harness).load_and_ingest()

    # DGA Hook
    hook = DGAAutomationHook(harness)
    updated = hook.sync_drought_decrees()
    
    # Basin 054 (Aconcagua) has an active decree in mock data
    assert updated > 0

    # Verify that the Aconcagua Juntas in the graph now have drought decree active
    juntas = harness.graph.find_nodes_by_label("JuntaVigilancia", bounded_context="OUA")
    aconcagua_juntas = [j for j in juntas if j.properties.get("cuenca_codigo") == "054"]
    assert len(aconcagua_juntas) > 0
    for j in aconcagua_juntas:
        assert j.properties.get("decreto_escasez_activo") is True
        assert "Decreto MOP" in j.properties.get("decreto_vigente_numero")


def test_dga_hook_triggers_critical_flow_event_on_deficit():
    client = DGAClientAdapter()
    harness = KnowledgeHarness()
    hook = DGAAutomationHook(harness, client)

    # El Manzano has 42.5 m3/s in mock. If required ecological is 50.0 m3/s -> Deficit event!
    event = hook.process_station_telemetry(codigo_bna="05701001-8", caudal_ecologico_minimo_m3s=50.0)
    assert event is not None
    assert event.event_name == "CaudalCriticoDetectado"
    assert event.payload["deficit"] == 7.5

    # If required ecological is 30.0 m3/s -> Normal (no alert)
    normal = hook.process_station_telemetry(codigo_bna="05701001-8", caudal_ecologico_minimo_m3s=30.0)
    assert normal is None
