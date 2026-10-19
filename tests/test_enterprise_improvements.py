"""
Tests unitarios y de integración para las mejoras de nivel empresarial:
1. Validadores y DTOs Pydantic v2 para catastros oficiales abiertos.
2. Hardening de seguridad OWASP, Token Bucket Rate Limiting y API Key Validator.
3. SQLite Embedded Knowledge Store con FTS5 BM25 y consultas espaciales B-Tree.
4. Motor de Búsqueda Híbrida tolerante a errores tipográficos (Token O(1) + BM25 + Fuzzy).
5. Endpoints /api/consulta/avanzada y /api/nodos/spatial.
"""

import os
import pytest
from pydantic import ValidationError
from starlette.testclient import TestClient

from src.domain.schemas.catalog_dtos import (
    IncendioRawDTO,
    DemandaAgricolaRawDTO,
    PredioRiegoRawDTO,
    DesaladoraRawDTO,
    EmbalseOficialRawDTO,
    RelaveRawDTO,
    HumedalProtegidoDTO
)
from src.api.security import (
    SecurityHeadersMiddleware,
    TokenBucketRateLimiter,
    verify_api_key
)
from src.memory.graph import DomainKnowledgeGraph, DomainNode, DomainEdge
from src.memory.sqlite_store import SQLiteKnowledgeStore
from src.domain.analytics.hybrid_search import HybridSearchEngine, fuzzy_similarity
from src.api.server import app

client = TestClient(app)


# =====================================================================
# 1. Tests de DTOs Fuertemente Tipados (Pydantic v2)
# =====================================================================

def test_incendio_raw_dto_valid():
    dto = IncendioRawDTO(
        id="INC-2023-VALP-001",
        nombre="Fuego El Olivar",
        comuna="Viña del Mar",
        region="Valparaíso",
        cuenca_codigo="054",
        superficie_ha=125.5,
        fecha_inicio="2023-12-15",
        latitud=-33.02,
        longitud=-71.55
    )
    assert dto.id == "INC-2023-VALP-001"
    assert dto.superficie_ha == 125.5
    assert dto.latitud == -33.02


def test_incendio_raw_dto_invalid_latitude():
    with pytest.raises(ValidationError):
        IncendioRawDTO(
            id="INC-BAD",
            nombre="Fuego Test",
            comuna="Test",
            region="Valparaíso",
            cuenca_codigo="054",
            superficie_ha=10.0,
            fecha_inicio="2024-01-01",
            latitud=95.0,  # Fuera del rango [-90.0, 90.0]
            longitud=-71.0
        )


def test_demanda_agricola_raw_dto():
    dto = DemandaAgricolaRawDTO(
        cuenca_codigo="057",
        cuenca_nombre="Río Maipo",
        superficie_regada_total_ha=85000.0,
        demanda_hidrica_bruta_m3_ano=1450.5,
        porcentaje_tecnificacion=68.0,
        cultivos_principales=["Frutales", "Viñedos", "Hortalizas"]
    )
    assert dto.cuenca_codigo == "057"
    assert dto.porcentaje_tecnificacion == 68.0
    assert len(dto.cultivos_principales) == 3


def test_predio_riego_raw_dto():
    dto = PredioRiegoRawDTO(
        id="PREDIO-001",
        nombre_valle="Valle del Maipo",
        comuna="Paine",
        cuenca_codigo="057",
        superficie_ha=45.0,
        sistema_riego="Goteo",
        latitud=-33.81,
        longitud=-70.74
    )
    assert dto.sistema_riego == "Goteo"
    assert dto.latitud == -33.81


def test_desaladora_raw_dto():
    dto = DesaladoraRawDTO(
        id="DESAL-01",
        nombre="Planta Desaladora Caldera",
        cuenca_codigo="034",
        capacidad_lps=1000.0,
        tecnologia="Osmosis Inversa",
        coordenadas=[-27.05, -70.81]
    )
    assert dto.capacidad_lps == 1000.0
    assert dto.tecnologia == "Osmosis Inversa"


def test_embalse_oficial_raw_dto():
    dto = EmbalseOficialRawDTO(
        id="EMB-01",
        nombre="Embalse El Yeso",
        cuenca_codigo="057",
        uso="AGUA POTABLE",
        coordenadas=[-33.67, -70.08]
    )
    assert dto.uso == "AGUA POTABLE"
    assert dto.cuenca_codigo == "057"


def test_relave_raw_dto():
    dto = RelaveRawDTO(
        id="REL-01",
        nombre="Tranque Mauque",
        comuna="Illapel",
        region="Coquimbo",
        cuenca_codigo="047",
        estado_operativo="Inactivo",
        volumen_total_actual_m3=5000000.0,
        coordenadas=[-31.62, -71.16]
    )
    assert dto.estado_operativo == "Inactivo"
    assert dto.volumen_total_actual_m3 == 5000000.0


def test_humedal_protegido_dto():
    dto = HumedalProtegidoDTO(
        id="HUM-01",
        nombre="Humedal Río Maipo",
        comuna="Santo Domingo",
        region="Valparaíso",
        cuenca_codigo="057",
        superficie_ha=40.0,
        resolucion_mma="D.S. 41/2020 MMA",
        coordenadas=[-33.61, -71.62]
    )
    assert dto.resolucion_mma == "D.S. 41/2020 MMA"
    assert dto.superficie_ha == 40.0


# =====================================================================
# 2. Tests de Hardening de Seguridad, Headers y Rate Limiting
# =====================================================================

def test_owasp_security_headers_present():
    """Verifica que las cabeceras de seguridad OWASP son inyectadas en todas las respuestas."""
    response = client.get("/")
    assert response.status_code == 200
    headers = response.headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert "1; mode=block" in headers["x-xss-protection"]
    assert headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "geolocation=()" in headers["permissions-policy"]


def test_token_bucket_rate_limiter_logic():
    """Valida el algoritmo token bucket: deducción, rechazo y recarga."""
    limiter = TokenBucketRateLimiter(capacity=3, refill_rate_per_sec=10.0)

    # 3 peticiones deben ser permitidas
    allowed1, wait1 = limiter.is_allowed("192.168.1.10")
    allowed2, wait2 = limiter.is_allowed("192.168.1.10")
    allowed3, wait3 = limiter.is_allowed("192.168.1.10")
    assert allowed1 is True
    assert allowed2 is True
    assert allowed3 is True

    # La 4ta petición inmediata debe ser rechazada
    allowed4, wait4 = limiter.is_allowed("192.168.1.10")
    assert allowed4 is False
    assert wait4 >= 1

    # Otra IP debe tener su propio bucket independiente
    allowed_other, _ = limiter.is_allowed("192.168.1.20")
    assert allowed_other is True


def test_verify_api_key_dev_mode(monkeypatch):
    """En ausencia de WATER_INTEL_API_KEY, el acceso local es irrestricto."""
    monkeypatch.delenv("WATER_INTEL_API_KEY", raising=False)
    res = verify_api_key(x_api_key=None, authorization=None)
    assert res == "dev-mode-unauthenticated"


def test_verify_api_key_production_mode(monkeypatch):
    """Con WATER_INTEL_API_KEY configurada, se exige token correcto."""
    monkeypatch.setenv("WATER_INTEL_API_KEY", "secret-super-key-123")

    # Rechazo si no se envía clave
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        verify_api_key(x_api_key=None, authorization=None)
    assert exc.value.status_code == 401

    # Rechazo si la clave es incorrecta
    with pytest.raises(HTTPException) as exc:
        verify_api_key(x_api_key="wrong-key", authorization=None)
    assert exc.value.status_code == 401

    # Aceptación con X-API-Key
    res_x = verify_api_key(x_api_key="secret-super-key-123", authorization=None)
    assert res_x == "secret-super-key-123"

    # Aceptación con Bearer Authorization
    res_b = verify_api_key(x_api_key=None, authorization="Bearer secret-super-key-123")
    assert res_b == "secret-super-key-123"


# =====================================================================
# 3. Tests de SQLite Knowledge Store (FTS5 + Bounding Box)
# =====================================================================

def test_sqlite_store_lifecycle_and_fts():
    """Crea una base SQLite en memoria, indexa un grafo y ejecuta FTS5 BM25."""
    store = SQLiteKnowledgeStore(db_path=":memory:")

    graph = DomainKnowledgeGraph()
    n1 = DomainNode(
        id="rio_01",
        label="Rio",
        bounded_context="Fisico",
        name="Río Maipo",
        properties={"cuenca_codigo": "057", "longitud_km": 250, "coordenadas": [-33.70, -70.80]}
    )
    n2 = DomainNode(
        id="canal_01",
        label="Canal",
        bounded_context="OUA",
        name="Canal San Carlos",
        properties={"cuenca_codigo": "057", "capacidad_lps": 15000, "coordenadas": [-33.45, -70.58]}
    )
    e1 = DomainEdge(
        source_id="rio_01",
        target_id="canal_01",
        relation_type="ALIMENTA_A",
        bounded_context="Fisico"
    )
    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_edge(e1)

    stats = store.sync_from_graph(graph)
    assert stats["nodes_indexed"] == 2
    assert stats["edges_indexed"] == 1
    assert stats["fts_indexed"] == 2

    # Búsqueda FTS5 BM25
    results = store.search_fts_bm25("Maipo")
    assert len(results) == 1
    assert results[0]["id"] == "rio_01"
    assert results[0]["bm25_rank"] is not None

    # Consulta Espacial por Bounding Box
    spatial_nodes = store.spatial_bbox_query(
        lat_min=-34.0, lat_max=-33.0, lon_min=-71.0, lon_max=-70.0
    )
    assert len(spatial_nodes) == 2

    # Conteo por etiquetas
    counts = store.count_by_label()
    assert counts["Rio"] == 1
    assert counts["Canal"] == 1


# =====================================================================
# 4. Tests de Motor de Búsqueda Híbrida (Tolerancia a Typos)
# =====================================================================

def test_fuzzy_similarity_utility():
    assert fuzzy_similarity("Río Maipo", "rio maipo") == 1.0
    assert fuzzy_similarity("Río Maipo", "rio mypo") >= 0.75
    assert fuzzy_similarity("Canal San Carlos", "totalmente diferente") < 0.3


def test_hybrid_search_typo_tolerance():
    """Valida que un error tipográfico encuentre la entidad correcta."""
    store = SQLiteKnowledgeStore(db_path=":memory:")
    graph = DomainKnowledgeGraph()
    graph.add_node(DomainNode(
        id="rio_maipo",
        label="Rio",
        bounded_context="Fisico",
        name="Río Maipo",
        properties={"cuenca_codigo": "057"}
    ))
    graph.add_node(DomainNode(
        id="embalse_el_yeso",
        label="Embalse",
        bounded_context="Infraestructura",
        name="Embalse El Yeso",
        properties={"cuenca_codigo": "057"}
    ))
    store.sync_from_graph(graph)

    engine = HybridSearchEngine(graph=graph, sqlite_store=store)

    # Coincidencia con error tipográfico en 'Río Maipo' -> 'rio mypo'
    res_typo = engine.search("rio mypo", limit=5)
    assert len(res_typo) > 0
    top_match = res_typo[0]
    assert top_match["id"] == "rio_maipo"
    assert top_match["relevance_score"] >= 0.60

    # Coincidencia con prefijo de embalse
    res_emb = engine.search("yeso", limit=5)
    assert len(res_emb) > 0
    assert any(r["id"] == "embalse_el_yeso" for r in res_emb)

    # Filtro por contexto
    res_context = engine.search("maipo", context_filter="Fisico")
    assert all(r["bounded_context"] == "Fisico" for r in res_context)


# =====================================================================
# 5. Tests de Endpoints REST Avanzados
# =====================================================================

def test_api_consulta_avanzada_endpoint():
    """Verifica el endpoint GET /api/consulta/avanzada con búsqueda tolerante a faltas."""
    response = client.get("/api/consulta/avanzada?q=maipo&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "maipo"
    assert data["total_encontrados"] > 0
    assert len(data["resultados"]) <= 5
    # Cada resultado debe tener la estructura esperada
    first = data["resultados"][0]
    assert "id" in first
    assert "label" in first
    assert "relevance_score" in first


def test_api_consulta_avanzada_typo():
    """Verifica que /api/consulta/avanzada tolere errores ortográficos."""
    response = client.get("/api/consulta/avanzada?q=rio mypo&limit=3")
    assert response.status_code == 200
    data = response.json()
    assert data["total_encontrados"] > 0


def test_api_nodos_spatial_endpoint():
    """Verifica el endpoint GET /api/nodos/spatial sobre la cuenca del Maipo / Santiago."""
    response = client.get(
        "/api/nodos/spatial?min_lat=-34.0&max_lat=-33.0&min_lon=-71.0&max_lon=-70.0&limit=10"
    )
    assert response.status_code == 200
    data = response.json()
    assert "bounding_box" in data
    assert data["total_encontrados"] > 0
    assert len(data["nodos"]) <= 10
    first = data["nodos"][0]
    assert "lat" in first and "lon" in first
    assert -34.0 <= first["lat"] <= -33.0
    assert -71.0 <= first["lon"] <= -70.0


def test_api_consulta_standard_endpoint_with_rate_limit():
    """Verifica que POST /api/consulta responda correctamente con el middleware de rate limit."""
    response = client.post(
        "/api/consulta",
        json={"consulta": "¿Cuáles son las cuencas del Río Maipo?", "contexto_delimitado": "Fisico"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "consulta_original" in data
    assert "nodos_relevantes_recuperados" in data
