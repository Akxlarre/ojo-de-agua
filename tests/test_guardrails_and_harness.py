"""
Unit tests for Ubiquitous Language Guardrails, Hydraulic Checks, and the Agentic Harness.
"""

import pytest
from src.guardrails.ubiquitous_linter import WaterUbiquitousGuard
from src.guardrails.hydraulic_guard import HydraulicGuardrail
from src.memory.graph import DomainEdge, DomainKnowledgeGraph, DomainNode
from src.harness.runner import KnowledgeHarness


def test_ubiquitous_guard_detects_forbidden_synonyms():
    guard = WaterUbiquitousGuard()
    # "comite de rio" is forbidden; canonical is "Junta de Vigilancia"
    # "guardia de compuerta" is forbidden; canonical is "Celador"
    text = "El comite de rio ordenó al guardia de compuerta abrir el canal."
    violations = guard.validate(text)
    
    assert len(violations) == 2
    found_forbidden = [v.forbidden_term_found for v in violations]
    assert "comite de rio" in found_forbidden
    assert "guardia de compuerta" in found_forbidden


def test_anti_corruption_layer_sanitizes_query():
    guard = WaterUbiquitousGuard()
    dirty_query = "¿Cuál es el rol del guardia de compuerta según el comite de rio?"
    clean_query = guard.sanitize_query(dirty_query)
    
    assert "Celador" in clean_query
    assert "Junta de Vigilancia" in clean_query
    assert "guardia de compuerta" not in clean_query
    assert "comite de rio" not in clean_query


def test_hydraulic_guardrail_mass_balance():
    # Influx: 10 m3/s. Extractions: 8 m3/s. Ecological flow: 3 m3/s -> Total: 11 m3/s -> Deficit!
    result = HydraulicGuardrail.validate_mass_balance(
        caudal_afluente_m3s=10.0,
        caudal_ecologico_m3s=3.0,
        extracciones_m3s={"Bocatoma 1": 5.0, "Bocatoma 2": 3.0}
    )
    assert not result.is_valid
    assert len(result.violations) == 1
    assert "GUARD-HIDRO-001" in result.violations[0]


def test_knowledge_harness_full_cycle():
    harness = KnowledgeHarness()

    # Create canonical nodes
    node_cuenca = DomainNode(
        id="cuenca-057",
        label="Cuenca",
        bounded_context="Fisico",
        name="Cuenca Río Maipo",
        properties={"codigo_dga": "057", "region": "Metropolitana"}
    )
    node_jv = DomainNode(
        id="jv-maipo-1",
        label="JuntaVigilancia",
        bounded_context="OUA",
        name="Junta de Vigilancia del Río Maipo Primera Sección",
        properties={"seccion": 1}
    )
    edge = DomainEdge(
        source_id="jv-maipo-1",
        target_id="cuenca-057",
        relation_type="ADMINISTRA_TRAMO_EN",
        bounded_context="OUA"
    )

    # Ingest through harness
    report = harness.ingest_candidate_elements(
        nodes=[node_cuenca, node_jv],
        edges=[edge]
    )

    assert report.success is True
    assert report.nodes_added == 2
    assert report.edges_added == 1
    assert len(report.lint_violations) == 0

    # Query with dirty language through the harness ACL
    agent_ctx = harness.prepare_agent_context(
        user_query="¿Qué hace el comite de rio en la Cuenca Río Maipo?",
        active_context="OUA"
    )

    # The ACL hook must have sanitized the query to "Junta de Vigilancia"
    assert "Junta de Vigilancia" in agent_ctx["sanitized_query"]
    assert len(agent_ctx["relevant_graph_nodes"]) > 0
    assert agent_ctx["relevant_graph_nodes"][0]["name"] == "Junta de Vigilancia del Río Maipo Primera Sección"
