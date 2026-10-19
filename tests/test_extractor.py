"""
Unit tests for the Automated Domain Document Extractor.
"""

import pytest
from src.harness.extractor import DomainDocumentExtractor
from src.harness.runner import KnowledgeHarness


def test_extractor_parses_entities_and_relationships():
    harness = KnowledgeHarness()
    extractor = DomainDocumentExtractor(harness)

    sample_doc = (
        "La Junta de Vigilancia del Río Aconcagua Primera Sección regula la "
        "Bocatoma San Rafael, la cual alimenta al Canal Los Andes. "
        "Las compuertas son inspeccionadas directamente por el celador Carlos Gómez, "
        "quien ejecutará el turno de prorrateo fijado por el directorio."
    )

    candidate = extractor.extract_from_text(sample_doc, source_reference="Acta Asamblea 2026")

    # Verify extracted entities
    labels = [n.label for n in candidate.nodes]
    assert "JuntaVigilancia" in labels
    assert "Bocatoma" in labels
    assert "Canal" in labels
    assert "Celador" in labels

    # Verify extracted topological edges
    relation_types = [e.relation_type for e in candidate.edges]
    assert "REGULA_EXTRACCION_EN" in relation_types
    assert "ALIMENTA_A" in relation_types
    assert "OPERA_COMPUERTA" in relation_types

    # Verify extracted invariant
    assert len(candidate.invariants) == 1
    assert candidate.invariants[0].name == "Prorrateo Obligatorio por Escasez"


def test_end_to_end_extraction_and_harness_guardrail():
    harness = KnowledgeHarness()
    extractor = DomainDocumentExtractor(harness)

    valid_doc = (
        "La Junta de Vigilancia del Río Huasco regula la Bocatoma Buena Esperanza, "
        "que entrega aguas al Canal Bellavista mediante el celador Manuel Castro."
    )

    report = extractor.extract_and_ingest(valid_doc, source_reference="Estatuto JV Huasco")
    assert report.success is True
    assert report.nodes_added == 4
    assert report.edges_added == 3
    assert len(report.lint_violations) == 0

    # Query graph to confirm presence
    ctx = harness.prepare_agent_context("¿Qué canal es alimentado por la Bocatoma Buena Esperanza?")
    assert len(ctx["relevant_graph_nodes"]) > 0
    node_names = [n["name"] for n in ctx["relevant_graph_nodes"]]
    assert any("Bocatoma Buena Esperanza" in name for name in node_names)
