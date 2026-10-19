"""
Unit tests for CrossDomainRelationBuilder and Causal Graph Edges.
"""

from src.domain.topological.cross_relations import CrossDomainRelationBuilder, haversine_km
from src.memory.graph import DomainKnowledgeGraph, DomainNode, DomainEdge


def test_haversine_km_calculation():
    # Distancia conocida: Santiago (-33.4489, -70.6693) a Valparaíso (-33.0472, -71.6127) ~ 98-105 km
    dist = haversine_km(-33.4489, -70.6693, -33.0472, -71.6127)
    assert 95.0 <= dist <= 110.0


def test_cross_domain_relation_builder():
    graph = DomainKnowledgeGraph()

    # 1. Agregar nodos sintéticos
    # Cuenca
    cuenca = DomainNode(
        id="cuenca-045",
        label="Cuenca",
        name="Cuenca Río Limarí",
        bounded_context="Fisico",
        properties={"codigo_dga": "045"}
    )
    graph.add_node(cuenca)

    # Relave abandonado en Ovalle
    relave = DomainNode(
        id="relave-test-1",
        label="DepositoRelave",
        name="Relave Test",
        bounded_context="mining_risk",
        properties={
            "estado_operativo": "ABANDONADO",
            "clasificacion_riesgo": "Crítico / Alto Riesgo",
            "region": "Coquimbo",
            "coordenadas": {"latitud": -30.55, "longitud": -71.18}
        }
    )
    graph.add_node(relave)

    # APR a 2 km del relave
    apr = DomainNode(
        id="apr-test-1",
        label="SistemaAPR",
        name="APR Lagunillas Test",
        bounded_context="drinking_water",
        properties={
            "region": "Coquimbo",
            "beneficiarios": 500,
            "coordenadas": [-30.54, -71.17]
        }
    )
    graph.add_node(apr)

    # PTAS
    ptas = DomainNode(
        id="ptas-test-1",
        label="PlantaTratamiento",
        name="PTAS Ovalle",
        bounded_context="sanitation",
        properties={
            "cuenca_codigo": "045",
            "cuerpo_receptor": "Río Limarí",
            "coordenadas": {"latitud": -30.60, "longitud": -71.20}
        }
    )
    graph.add_node(ptas)

    # Humedal Urbano a 5 km
    humedal = DomainNode(
        id="humedal-test-1",
        label="HumedalUrbano",
        name="Humedal Desembocadura Limarí",
        bounded_context="wetlands",
        properties={
            "cuenca_codigo": "045",
            "superficie_ha": 45.0,
            "coordenadas": {"latitud": -30.62, "longitud": -71.22}
        }
    )
    graph.add_node(humedal)

    # Central Hidroeléctrica > 20 MW
    hidro = DomainNode(
        id="hidro-test-1",
        label="CentralHidroelectrica",
        name="Central Paloma",
        bounded_context="energy",
        properties={
            "cuenca_codigo": "045",
            "potencia_mw": 25.0,
            "tipo_tecnologia": "Embalse"
        }
    )
    graph.add_node(hidro)

    # Junta de Vigilancia
    junta = DomainNode(
        id="jv-test-1",
        label="JuntaVigilancia",
        name="Junta de Vigilancia del Río Limarí",
        bounded_context="oua",
        properties={
            "cuenca_codigo": "045"
        }
    )
    graph.add_node(junta)

    # Planta Desaladora
    desal = DomainNode(
        id="desal-test-1",
        label="PlantaDesaladora",
        name="Desaladora Bahía Limarí",
        bounded_context="desalination",
        properties={
            "cuenca_codigo": "045",
            "capacidad_lps": 1000.0,
            "es_operativa": True,
            "sector_destino": "Minería"
        }
    )
    graph.add_node(desal)

    # Ejecutar constructor de relaciones cruzadas
    builder = CrossDomainRelationBuilder(graph)
    report = builder.build_all_cross_relations()

    assert report["amenaza_relave_apr_added"] >= 1
    assert report["descarga_ptas_humedal_added"] >= 1
    assert report["compite_hidro_riego_added"] >= 1
    assert report["alivio_desalacion_added"] >= 1

    # Verificar que los bordes existen en el grafo
    edges = graph.edges
    amenaza_edges = [e for e in edges if e.relation_type == "AMENAZA_AGUAS_ARRIBA"]
    assert len(amenaza_edges) == 1
    assert amenaza_edges[0].source_id == "relave-test-1"
    assert amenaza_edges[0].target_id == "apr-test-1"
    assert amenaza_edges[0].properties["distancia_km"] <= 5.0

    alivio_edges = [e for e in edges if e.relation_type == "ALIVIA_PRESION_HIDRICA"]
    assert len(alivio_edges) == 1
    assert alivio_edges[0].target_id == "cuenca-045"
