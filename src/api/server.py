"""
FastAPI Server for Chilean Water Governance & Agentic Knowledge Harness.
Exposes REST endpoints for:
- Interactive Leaflet.js GIS Map (/mapa)
- Querying 90 DGA Basins and 108 OUAs
- Deterministic Legal Prorating Engine (Ley 21.435 Art. 5 bis & Art. 18)
- Real-time MEE Telemetry Audit (Illegal Extraction Detection)
- Natural Language Domain Querying with ACL Sanitization
"""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from src.domain.operation.models import EstadoOrdenTurno, OrdenTurno
from src.domain.operation.prorrateo_service import (
    DemandaCanal,
    ProrrateoLegalService,
    ResultadoProrrateo,
)
from src.domain.physical.map_generator import ChileWaterMapGenerator
from src.guardrails.illegal_extraction_guard import (
    AlertaInfraccionDGA,
    IllegalExtractionGuardrail,
    LecturaSensorMEE,
)
from src.domain.analytics.diagnostic_service import HolisticCuencaDiagnosticService
from src.domain.operation.timeseries_store import LecturaTelemetrica, TimeseriesStore
from src.harness.runner import KnowledgeHarness
from src.memory.graph import DomainKnowledgeGraph
from src.api.security import SecurityHeadersMiddleware, check_rate_limit, verify_api_key

# Initialize FastAPI application
app = FastAPI(
    title="API de Gobernanza Hídrica y Harness DDD de Chile",
    description="Motor de inteligencia de dominio para Juntas de Vigilancia, Canales, DGA y Prorrateo Legal (Ley 21.435).",
    version="2.1.0"
)

# FAL-03: CORS Middleware para permitir clientes web, dashboards y SPAs
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enterprise Security Headers Middleware (OWASP)
app.add_middleware(SecurityHeadersMiddleware)

DATA_DIR = Path(__file__).parent.parent.parent / "data"
GRAPH_PATH = DATA_DIR / "knowledge_graph_chile.json"
MAP_PATH = DATA_DIR / "mapa_cuencas_chile.html"

# FAL-02: Caché en memoria para evitar I/O repetitivo de archivos JSON pesados
_DATASET_CACHE: Dict[str, Any] = {}

def get_cached_json(filename: str) -> Optional[Any]:
    """Carga y cachea en memoria los catastro JSON para respuestas sub-milisegundo."""
    if filename not in _DATASET_CACHE:
        path = DATA_DIR / filename
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            _DATASET_CACHE[filename] = json.load(f)
    return _DATASET_CACHE[filename]

# Load in-memory graph
harness = KnowledgeHarness()
if GRAPH_PATH.exists():
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        gdata = json.load(f)
        harness.graph = DomainKnowledgeGraph.from_dict(gdata)

from src.memory.sqlite_store import SQLiteKnowledgeStore
from src.domain.analytics.hybrid_search import HybridSearchEngine

diagnostic_service = HolisticCuencaDiagnosticService(data_dir=DATA_DIR)
timeseries_store = TimeseriesStore(storage_dir=DATA_DIR / "historical")
sqlite_store = SQLiteKnowledgeStore(db_path=str(DATA_DIR / "knowledge_graph_chile.db"))
hybrid_search = HybridSearchEngine(graph=harness.graph, sqlite_store=sqlite_store)

# Sincronización inicial si la base SQLite está vacía
if GRAPH_PATH.exists() and len(harness.graph.nodes) > 0:
    try:
        if not sqlite_store.count_by_label():
            sqlite_store.sync_from_graph(harness.graph)
    except Exception:
        pass


# --- Request & Response Models ---

class ProrrateoRequest(BaseModel):
    caudal_afluente_lps: float = Field(gt=0.0, description="Caudal disponible en el río (L/s)")
    caudal_ecologico_minimo_lps: float = Field(ge=0.0, description="Caudal ecológico legal reservado (L/s)")
    demandas_canales: List[DemandaCanal]


class AuditoriaRequest(BaseModel):
    lectura_mee: LecturaSensorMEE
    ordenes_activas: List[OrdenTurno] = Field(default_factory=list)


class ConsultaRequest(BaseModel):
    consulta: str = Field(description="Pregunta en lenguaje natural sobre ríos, canales o juntas")
    contexto_delimitado: Optional[str] = Field(default=None, description="'OUA', 'Fisico', 'Legal', 'Operacion'")


class ChatStreamRequest(BaseModel):
    consulta: str = Field(description="Pregunta en lenguaje natural para el Copiloto AI")
    cuenca_contexto: Optional[str] = Field(default=None, description="Código DGA de cuenca opcional")


class LoteTelemetricoRequest(BaseModel):
    lecturas: List[LecturaTelemetrica]
    ordenes_activas: Optional[List[OrdenTurno]] = Field(default_factory=list)


# --- Endpoints ---

@app.api_route("/", methods=["GET", "HEAD"], tags=["Estado"])
def index() -> Dict[str, Any]:
    """Retorna el estado de la base de conocimiento y métricas del grafo."""
    total_nodes = len(harness.graph.nodes)
    total_edges = len(harness.graph.edges)
    return {
        "status": "online",
        "sistema": "Harness de Conocimiento Agéntico - Aguas de Chile",
        "marco_legal": "Código de Aguas (DFL 1.122) y Ley 21.435 (Reforma 2022)",
        "grafo_conocimiento": {
            "total_nodos": total_nodes,
            "total_relaciones": total_edges,
            "cuencas_oficiales": len(harness.graph.find_nodes_by_label("Cuenca")),
            "juntas_vigilancia": len(harness.graph.find_nodes_by_label("JuntaVigilancia")),
            "asociaciones_canalistas": len(harness.graph.find_nodes_by_label("AsociacionCanalistas")),
            "canales_matrices": len(harness.graph.find_nodes_by_label("Canal"))
        },
        "mapa_url": "/mapa"
    }


@app.api_route("/mapa", methods=["GET", "HEAD"], response_class=HTMLResponse, tags=["GIS & Mapas"])
def ver_mapa_interactivo():
    """Sirve el mapa interactivo de Chile en Leaflet.js con las 90 cuencas y alertas de sequía."""
    generator = ChileWaterMapGenerator(str(DATA_DIR))
    map_file = generator.generate_html_map(str(MAP_PATH))
    with open(map_file, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/api/cuencas", tags=["Catastro DGA"])
def listar_cuencas(
    region: Optional[str] = Query(None, description="Filtrar por región (ej: 'Metropolitana', 'Maule')"),
    zona: Optional[str] = Query(None, description="'Norte Grande', 'Norte Chico', 'Zona Central', 'Zona Sur', 'Zona Austral'")
) -> List[Dict[str, Any]]:
    """Lista las cuencas oficiales de Chile catastradas por la DGA."""
    data = get_cached_json("cuencas_dga_chile.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Catastro de cuencas no encontrado.")

    if region:
        data = [c for c in data if region.lower() in c.get("region", "").lower()]
    if zona:
        data = [c for c in data if zona.lower() in c.get("zona_hidrografica", "").lower()]
    return data


@app.get("/api/ouas", tags=["Organizaciones de Usuarios"])
def listar_organizaciones_usuarios(
    cuenca: Optional[str] = Query(None, description="Código DGA de la cuenca (ej: '057', '054')"),
    tipo: Optional[str] = Query(None, description="'Junta de Vigilancia' o 'Asociación de Canalistas'")
) -> List[Dict[str, Any]]:
    """Lista las Juntas de Vigilancia y Asociaciones de Canalistas registradas."""
    data = get_cached_json("registro_nacional_ouas.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Registro de OUAs no encontrado.")

    if cuenca:
        data = [o for o in data if o.get("cuenca_codigo") == cuenca]
    if tipo:
        data = [o for o in data if tipo.lower() in o.get("tipo", "").lower()]
    return data


@app.get("/api/shac", tags=["Aguas Subterráneas (SHAC)"])
def listar_sectores_hidrogeologicos(
    cuenca: Optional[str] = Query(None, description="Código BNA de la cuenca"),
    region: Optional[str] = Query(None, description="Nombre de la región")
) -> List[Dict[str, Any]]:
    """Lista los Sectores Hidrogeológicos de Aprovechamiento Común (SHAC) oficiales."""
    data = get_cached_json("shac_chile.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Catastro de SHACs no encontrado.")
    if cuenca:
        data = [s for s in data if s.get("codigo_cuenca_bna") == cuenca]
    if region:
        data = [s for s in data if region.lower() in (s.get("region") or "").lower()]
    return data


@app.get("/api/estaciones-bna", tags=["Red Hidrométrica BNA"])
def listar_estaciones_bna(
    cuenca: Optional[str] = Query(None, description="Código de la cuenca DGA"),
    tipo: Optional[str] = Query(None, description="FLUVIOMETRICA, CONTROL DE NIVEL, etc.")
) -> List[Dict[str, Any]]:
    """Lista las estaciones de monitoreo de la Red Hidrométrica Nacional de la DGA."""
    data = get_cached_json("estaciones_bna_chile.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Inventario de estaciones BNA no encontrado.")
    if cuenca:
        data = [s for s in data if s.get("codigo_cuenca") == cuenca]
    if tipo:
        data = [s for s in data if tipo.lower() in (s.get("tipo") or "").lower()]
    return data[:200]  # Limitar a 200 resultados para respuesta ágil


@app.get("/api/decretos-escasez", tags=["Decretos de Escasez Hídrica"])
def listar_decretos_escasez(
    vigente: Optional[bool] = Query(None, description="Filtrar solo decretos actualmente vigentes"),
    region: Optional[str] = Query(None, description="Filtrar por región")
) -> List[Dict[str, Any]]:
    """Lista los Decretos de Escasez Hídrica dictados por el MOP bajo el Art. 314."""
    data = get_cached_json("decretos_escasez_chile.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Registro de decretos no encontrado.")
    if vigente is not None:
        data = [d for d in data if d.get("es_vigente") == vigente]
    if region:
        data = [d for d in data if region.lower() in (d.get("region") or "").lower()]
    return data


@app.get("/api/patentes-no-uso", tags=["Fiscalización y Especulación (TGR)"])
def consultar_patentes_no_uso(
    comuna: Optional[str] = Query(None, description="Filtrar por comuna crítica"),
    region: Optional[str] = Query(None, description="Filtrar por región")
) -> Dict[str, Any]:
    """
    Retorna el informe consolidado de derechos de agua retenidos bajo cobro de Patente
    por No Uso (Art. 129 bis Código de Aguas), liquidado por la Tesorería General de la República.
    """
    data = get_cached_json("patentes_no_uso_chile.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Dataset de patentes TGR no encontrado.")

    if comuna:
        com_list = [c for c in data.get("ranking_comunas_top_25", []) if comuna.lower() in c["comuna"].lower()]
        titulares_com = [t for t in data.get("ranking_titulares_top_50", []) if comuna.lower() in t["comuna_principal"].lower()]
        return {
            "filtro_comuna": comuna,
            "metricas_comuna": com_list,
            "titulares_en_comuna": titulares_com
        }

    if region:
        reg_list = [r for r in data.get("ranking_regiones", []) if region.lower() in r["region"].lower()]
        return {
            "filtro_region": region,
            "metricas_region": reg_list
        }

    return data


@app.get("/api/camels-cl", tags=["Hidroclima y Cuencas (CAMELS-CL)"])
def listar_cuencas_camels(
    codigo_bna: Optional[str] = Query(None, description="Código BNA de la estación principal"),
    intervencion: Optional[str] = Query(None, description="Filtro por grado de intervención antrópica")
) -> List[Dict[str, Any]]:
    """
    Retorna atributos hidroclimáticos oficiales de cuencas CAMELS-CL (CR2 / U. de Chile / PANGAEA):
    precipitación media CR2MET, evapotranspiración potencial, aridez, escorrentía e intervención antrópica.
    """
    data = get_cached_json("camels_cl_cuencas.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Dataset CAMELS-CL no encontrado.")
    if codigo_bna:
        data = [c for c in data if codigo_bna in c.get("codigo_bna", "")]
    if intervencion:
        data = [c for c in data if intervencion.lower() in (c.get("grado_intervencion_antropica") or "").lower()]
    return data[:200]


@app.get("/api/sistemas-apr", tags=["Consumo Humano y APR (DOH / Art. 5 bis)"])
def listar_sistemas_apr(
    comuna: Optional[str] = Query(None, description="Filtrar por comuna"),
    region: Optional[str] = Query(None, description="Filtrar por región")
) -> List[Dict[str, Any]]:
    """
    Lista los Sistemas Sanitarios Rurales (Comités y Cooperativas de Agua Potable Rural APR)
    georreferenciados por la Dirección de Obras Hidráulicas (DOH - MOP).
    Fundamental para la priorización legal de caudales bajo el Art. 5 bis del Código de Aguas.
    """
    data = get_cached_json("sistemas_ssr_apr_chile.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Dataset de Sistemas SSR / APR no encontrado.")
    if comuna:
        data = [s for s in data if comuna.lower() in (s.get("comuna") or "").lower()]
    if region:
        data = [s for s in data if region.lower() in (s.get("region") or "").lower()]
    return data[:300]


@app.get("/api/glaciares", tags=["Criósfera y Glaciares (DGA - IPG)"])
def listar_glaciares(
    cuenca: Optional[str] = Query(None, description="Código DGA de la cuenca receptora (ej. 057, 054, 115)"),
    tipo: Optional[str] = Query(None, description="GLACIAR DE MONTAÑA, GLACIAR ROCOSO, GLACIAR DE VALLE, etc."),
    nombre: Optional[str] = Query(None, description="Nombre o parte del nombre del glaciar"),
    limit: int = Query(200, ge=1, le=1000, description="Límite de resultados a retornar"),
    offset: int = Query(0, ge=0, description="Offset de paginación")
) -> Dict[str, Any]:
    """
    Retorna el catastro de glaciares del Inventario Público de Glaciares de Chile (DGA - IPG 2022).
    Reservas estratégicas protegidas expresamente contra constitución de derechos de aprovechamiento
    bajo el Art. 5 bis de la Ley 21.435.
    """
    data = get_cached_json("glaciares_chile.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Dataset de glaciares no encontrado.")

    if cuenca:
        data = [g for g in data if g.get("cuenca_codigo") == cuenca]
    if tipo:
        data = [g for g in data if tipo.lower() in (g.get("clasificacion") or "").lower()]
    if nombre:
        data = [g for g in data if nombre.lower() in (g.get("nombre") or "").lower()]

    total_filtrados = len(data)
    items = data[offset : offset + limit]
    return {
        "total_coincidentes": total_filtrados,
        "limit": limit,
        "offset": offset,
        "glaciares": items
    }


@app.get("/api/glaciares/resumen-cuencas", tags=["Criósfera y Glaciares (DGA - IPG)"])
def resumen_crioclimatico_cuencas(
    cuenca: Optional[str] = Query(None, description="Código de la cuenca DGA (ej. 057)")
) -> List[Dict[str, Any]]:
    """
    Retorna el balance y reservas criosféricas agregadas por macrocuenca hidrográfica:
    superficie total de hielo (km²), volumen estimado (km³) y equivalente en agua dulce (km³).
    """
    data = get_cached_json("glaciares_resumen_cuencas.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Resumen de glaciares por cuenca no encontrado.")
    if cuenca:
        data = [c for c in data if c.get("cuenca_codigo") == cuenca]
    return data


@app.get("/api/canales-riego", tags=["Infraestructura y Fomento al Riego (CNR / CIREN)"])
def listar_canales_riego(
    cuenca: Optional[str] = Query(None, description="Código DGA de la cuenca (ej. 057, 073, 081)"),
    junta_vigilancia: Optional[str] = Query(None, description="Filtro por Junta de Vigilancia"),
    fuente: Optional[str] = Query(None, description="Filtro por río o fuente hídrica"),
    nombre: Optional[str] = Query(None, description="Filtro por nombre del canal"),
    limit: int = Query(200, ge=1, le=1000, description="Límite de resultados a retornar"),
    offset: int = Query(0, ge=0, description="Offset de paginación")
) -> Dict[str, Any]:
    """
    Retorna el Catastro Nacional de Canales de Riego de Chile (Comisión Nacional de Riego CNR / CIREN).
    Contiene 12.233 canales georreferenciados con longitud, trazado, organizaciones de usuarios y fuentes.
    """
    data = get_cached_json("canales_riego_chile.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Dataset de canales no encontrado.")

    if cuenca:
        data = [c for c in data if c.get("cuenca_codigo") == cuenca]
    if junta_vigilancia:
        data = [c for c in data if junta_vigilancia.lower() in (c.get("junta_vigilancia") or "").lower()]
    if fuente:
        data = [c for c in data if fuente.lower() in (c.get("fuente_hidrica") or "").lower()]
    if nombre:
        data = [c for c in data if nombre.lower() in (c.get("nombre") or "").lower()]

    total_filtrados = len(data)
    items = data[offset : offset + limit]
    return {
        "total_coincidentes": total_filtrados,
        "limit": limit,
        "offset": offset,
        "canales": items
    }


@app.get("/api/canales-riego/resumen-cuencas", tags=["Infraestructura y Fomento al Riego (CNR / CIREN)"])
def resumen_canales_cuencas(
    cuenca: Optional[str] = Query(None, description="Código de la cuenca DGA (ej. 057, 081)")
) -> List[Dict[str, Any]]:
    """
    Retorna la densidad de infraestructura de conducción por macrocuenca:
    número de canales, longitud total de la red (km), Juntas de Vigilancia y canales matrices principales.
    """
    data = get_cached_json("canales_resumen_cuencas.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Resumen de canales por cuenca no encontrado.")
    if cuenca:
        data = [c for c in data if c.get("cuenca_codigo") == cuenca]
    return data



@app.post("/api/prorrateo", response_model=ResultadoProrrateo, tags=["Simulación Hidráulica"])
def calcular_prorrateo_legal(req: ProrrateoRequest):
    """
    Ejecuta el cálculo determinista de distribución de caudales aplicando
    la prioridad de Consumo Humano (Art. 5 bis) y la regla de Permanentes vs Eventuales (Art. 18).
    """
    resultado = ProrrateoLegalService.calcular_distribucion(
        caudal_afluente_lps=req.caudal_afluente_lps,
        caudal_ecologico_minimo_lps=req.caudal_ecologico_minimo_lps,
        demandas_canales=req.demandas_canales
    )
    return resultado


@app.post("/api/auditoria/extraccion", tags=["Guardrails & Fiscalización"])
def auditar_extraccion_mee(req: AuditoriaRequest):
    """
    Audita en tiempo real una lectura telemétrica de sensor MEE contra las órdenes
    de turno activas de la OUA para detectar extracciones ilegales o sobregiros.
    """
    alerta = IllegalExtractionGuardrail.auditar_extraccion(
        lectura_mee=req.lectura_mee,
        ordenes_activas=req.ordenes_activas
    )
    if alerta:
        return {
            "infraccion_detectada": True,
            "alerta": alerta.model_dump()
        }
    return {
        "infraccion_detectada": False,
        "mensaje": "Extracción conforme a derecho dentro de los márgenes autorizados."
    }


@app.post("/api/consulta", tags=["Asistente Agéntico"], dependencies=[Depends(check_rate_limit)])
def consultar_grafo_conocimiento(req: ConsultaRequest):
    """
    Ejecuta la consulta agéntica con Capa Anti-Corrupción (ACL) para normalizar
    jerga coloquial hacia el Lenguaje Ubicuo y recuperar el subgrafo relevante.
    """
    ctx = harness.prepare_agent_context(
        user_query=req.consulta,
        active_context=req.contexto_delimitado
    )
    return {
        "consulta_original": ctx["original_query"],
        "consulta_sanitizada_acl": ctx["sanitized_query"],
        "contexto_delimitado": ctx["bounded_context"],
        "nodos_relevantes_recuperados": ctx["relevant_graph_nodes"][:10],
        "total_encontrados": len(ctx["relevant_graph_nodes"])
    }


@app.post("/api/chat/stream", tags=["Copiloto AI"])
async def stream_chat_agente(req: ChatStreamRequest):
    """
    Endpoint Server-Sent Events (SSE) para el Copiloto Agéntico de Gobernanza Hídrica.
    Emite en streaming pensamientos (Chain of Thought), artefactos vivos de Generative UI,
    citas jurídicas vinculantes y fragmentos de síntesis analítica en tiempo real.
    """
    async def event_generator():
        try:
            # 1. Thought Step 1: Normalización ACL
            thought_1 = {
                "id": str(uuid.uuid4())[:8],
                "pasoNumero": 1,
                "titulo": "Normalizando jerga y aplicando Capa Anti-Corrupción (ACL)...",
                "detalle": f"Analizando query '{req.consulta[:60]}...' contra el Lenguaje Ubicuo.",
                "tiempoEjecucionMs": 15,
                "herramientaInvocada": "AntiCorruptionLayer"
            }
            yield f"data: {json.dumps({'tipo': 'thought', 'thought': thought_1}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.08)

            # Preparar contexto agéntico
            ctx = harness.prepare_agent_context(
                user_query=req.consulta,
                active_context=None
            )
            nodos = ctx.get("relevant_graph_nodes", [])
            query_sanitizada = ctx.get("sanitized_query", req.consulta)

            # Identificar cuenca relevante (por parámetro o por nodo recuperado)
            cuenca_cod = req.cuenca_contexto
            if not cuenca_cod and nodos:
                for n in nodos:
                    if n.get("bounded_context") == "Fisico" and n.get("properties", {}).get("codigo_dga"):
                        cuenca_cod = n["properties"]["codigo_dga"]
                        break
                    elif n.get("id", "").startswith("CUENCA_"):
                        cuenca_cod = n["id"].replace("CUENCA_", "")
                        break

            # 2. Thought Step 2: Búsqueda en Grafo y balance hídrico
            thought_2 = {
                "id": str(uuid.uuid4())[:8],
                "pasoNumero": 2,
                "titulo": "Búsqueda topológica y recuperación de atributos de derechos de agua...",
                "detalle": f"Recuperados {len(nodos)} nodos en subgrafo relevante.",
                "tiempoEjecucionMs": 35,
                "herramientaInvocada": "KnowledgeGraphHarness"
            }
            yield f"data: {json.dumps({'tipo': 'thought', 'thought': thought_2}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.08)

            # 3. Artefacto en caso de haber identificado cuenca
            diag_data = None
            if cuenca_cod:
                try:
                    diag_data = diagnostic_service.calcular_diagnostico_cuenca(cuenca_cod)
                except Exception:
                    diag_data = None

            if diag_data:
                artifact = {
                    "id": f"art-{cuenca_cod}",
                    "tipo": "cuenca_kpi",
                    "titulo": f"Diagnóstico de Seguridad Hídrica: {diag_data.get('nombre_cuenca', cuenca_cod)}",
                    "subtitulo": f"Código DGA {cuenca_cod} | Categoría: {diag_data.get('clasificacion', 'MODERADO')}",
                    "cuencaCodigo": cuenca_cod,
                    "datosDiagnostico": diag_data
                }
                yield f"data: {json.dumps({'tipo': 'artifact', 'artifact': artifact}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.08)

            # 4. Cita jurídica vinculante
            citation = {
                "id": "cit-ley-21435-art5",
                "norma": "Ley 21.435 (Reforma Código de Aguas)",
                "articulo": "Art. 5 bis",
                "descripcion": "El acceso al agua potable y saneamiento es un derecho humano esencial. Se prioriza siempre el consumo humano por sobre el uso productivo en situaciones de escasez o prorrateo.",
                "urlOficial": "https://www.bcn.cl/leychile/navegar?idNorma=1174662"
            }
            yield f"data: {json.dumps({'tipo': 'citation', 'citation': citation}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)

            # 5. Generar contenido estructurado de respuesta
            nombre_cuenca = diag_data.get("nombre_cuenca", "Nacional") if diag_data else "la cuenca seleccionada"
            clasificacion = diag_data.get("clasificacion", "OPERATIVO") if diag_data else "MONITOREO"
            indice_estres = diag_data.get("indice_estres_hidrico", 0.0) if diag_data else 0.0
            total_apr = diag_data.get("total_apr", 0) if diag_data else 0
            apr_vulnerables = len(diag_data.get("apr_vulnerables", [])) if diag_data else 0

            respuesta_text = (
                f"### Evaluación Agéntica del Sistema Hídrico\n\n"
                f"De acuerdo con el análisis del Grafo de Conocimiento y los registros oficiales de la DGA, "
                f"la consulta sobre **{query_sanitizada}** ha sido contextualizada en el marco regulatorio vigente "
                f"(Ley 21.435 y DFL 1.122).\n\n"
            )

            if diag_data:
                respuesta_text += (
                    f"**Cuenca Focal:** {nombre_cuenca} (DGA `{cuenca_cod}`)\n"
                    f"- **Nivel de Estrés:** `{clasificacion}` (Índice: {indice_estres:.2f})\n"
                    f"- **Comités APR / SSR:** {total_apr} sistemas registrados ({apr_vulnerables} en condición de vulnerabilidad crítica)\n"
                    f"- **Dictamen Operativo:** En caso de activación de decreto de escasez hídrica, la Junta de Vigilancia respectiva "
                    f"debe someterse a prorrateo legal estricto resguardando en primer lugar el caudal ecológico mínimo y el consumo humano.\n\n"
                )
            elif nodos:
                nombres_destacados = ", ".join([n.get("name", "") for n in nodos[:4] if n.get("name")])
                respuesta_text += (
                    f"Se identificaron entidades clave en la red hidrográfica y legal: **{nombres_destacados}**.\n"
                    f"Los titulares de derechos consuntivos superficiales y subterráneos se encuentran regidos por las reglas "
                    f"de distribución proporcional de la Junta de Vigilancia respectiva bajo la supervigilancia de la DGA.\n\n"
                )
            else:
                respuesta_text += (
                    f"El sistema ha consultado la red nacional de 90 cuencas y 108 Organizaciones de Usuarios de Agua (OUA). "
                    f"Puedes seleccionar una cuenca específica en el mapa interactivo o ingresar su nombre/código DGA "
                    f"para obtener una simulación de prorrateo y auditoría MEE en tiempo real.\n\n"
                )

            respuesta_text += (
                f"> **Garantía Legal:** Todo acuerdo de redistribución debe ser aprobado por la DGA (Art. 314) y "
                f"respetar la ordenanza de telemetría DGA Res. Exenta N° 1238/2019."
            )

            # Stream chunks (palabras/frases)
            words = respuesta_text.split(" ")
            for i in range(0, len(words), 3):
                chunk = " ".join(words[i:i+3]) + " "
                yield f"data: {json.dumps({'tipo': 'chunk', 'contenido': chunk}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.03)

            # Evento final de cierre
            yield f"data: {json.dumps({'tipo': 'done'}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'tipo': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'tipo': 'done'}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "X-Accel-Buffering": "no",
        }
    )


@app.get("/api/consulta/avanzada", tags=["Asistente Agéntico"], dependencies=[Depends(check_rate_limit)])
def consulta_avanzada_hibrida(
    q: str = Query(..., min_length=1, description="Término de búsqueda o consulta en lenguaje natural"),
    contexto: Optional[str] = Query(None, description="Filtro opcional por Bounded Context (ej. Fisico, Legal, OUA)"),
    limit: int = Query(20, ge=1, le=100, description="Cantidad máxima de resultados")
) -> Dict[str, Any]:
    """
    Búsqueda híbrida multi-estrategia (Token O(1) + SQLite FTS5 BM25 + Fuzzy Levenshtein).
    Resistente a errores tipográficos y variaciones coloquiales (ej. 'rio mypo', 'canall', 'embalse penuelas').
    """
    results = hybrid_search.search(query=q, limit=limit, context_filter=contexto)
    return {
        "query": q,
        "contexto_filtro": contexto,
        "total_encontrados": len(results),
        "resultados": results
    }


@app.get("/api/nodos/spatial", tags=["Grafo de Conocimiento & Espacial"])
def consultar_nodos_espaciales(
    min_lat: float = Query(..., description="Latitud mínima (ej. -34.0)"),
    max_lat: float = Query(..., description="Latitud máxima (ej. -32.5)"),
    min_lon: float = Query(..., description="Longitud mínima (ej. -71.5)"),
    max_lon: float = Query(..., description="Longitud máxima (ej. -69.8)"),
    label: Optional[str] = Query(None, description="Etiqueta opcional de nodo (ej. Rio, Cuenca, Canal, Embalse, EstacionBNA)"),
    context: Optional[str] = Query(None, description="Bounded Context opcional (ej. Fisico, OUA)"),
    limit: int = Query(500, ge=1, le=5000, description="Límite de nodos a retornar")
) -> Dict[str, Any]:
    """
    Consulta espacial mediante Bounding Box sobre el almacén SQLite de nodos georreferenciados.
    Permite filtrar eficientemente por coordenadas geográficas con índices B-Tree en latitud y longitud.
    """
    nodes = sqlite_store.spatial_bbox_query(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        label=label,
        context=context,
        limit=limit
    )
    return {
        "bounding_box": {
            "min_lat": min_lat,
            "max_lat": max_lat,
            "min_lon": min_lon,
            "max_lon": max_lon
        },
        "total_encontrados": len(nodes),
        "nodos": nodes
    }


# --- Fiscalización y Cumplimiento Ambiental (SMA / SNIFA) ---

@app.get("/api/sma/sanciones", tags=["Fiscalización Ambiental (SMA / SNIFA)"])
def listar_sanciones_ambientales(
    cuenca: Optional[str] = Query(None, description="Código DGA de la cuenca (ej. 057, 034, 054)"),
    sector: Optional[str] = Query(None, description="Categoría económica (ej. Minería, Agroindustrias, Saneamiento Ambiental)"),
    estado: Optional[str] = Query(None, description="Estado del proceso (ej. 'Terminado - Sanción', 'En curso')"),
    min_uta: Optional[float] = Query(0.0, ge=0.0, description="Multa mínima en UTA"),
    solo_agua: bool = Query(False, description="Filtrar solo procesos vinculados a recursos hídricos / RILES / D.S. 90 / D.S. 46"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """
    Retorna el catastro de procesos sancionatorios de la SMA / SNIFA con filtros
    por cuenca hidrográfica DGA, sector económico y afección a recursos hídricos.
    """
    data = get_cached_json("sma_sanciones_agua_chile.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Dataset de sanciones SMA no encontrado.")

    if cuenca:
        data = [s for s in data if s.get("cuenca_codigo") == cuenca]
    if sector:
        data = [s for s in data if sector.lower() in (s.get("categoria_economica") or "").lower()]
    if estado:
        data = [s for s in data if estado.lower() in (s.get("estado") or "").lower()]
    if min_uta and min_uta > 0:
        data = [s for s in data if (s.get("multa_total_uta") or 0.0) >= min_uta]
    if solo_agua:
        data = [s for s in data if s.get("es_relevante_agua")]

    total_filtrados = len(data)
    items = data[offset : offset + limit]
    return {
        "total_coincidentes": total_filtrados,
        "limit": limit,
        "offset": offset,
        "sanciones": items
    }


@app.get("/api/sma/resumen-cuencas", tags=["Fiscalización Ambiental (SMA / SNIFA)"])
def resumen_sanciones_cuencas(
    cuenca: Optional[str] = Query(None, description="Código DGA de la cuenca (ej. 057, 030, 112)")
) -> List[Dict[str, Any]]:
    """
    Retorna la síntesis de infracciones y multas ambientales de la SMA agregadas por macrocuenca:
    monto total acumulado de multas en UTA, procesos de relevancia hídrica y casos paradigmáticos.
    """
    data = get_cached_json("sma_resumen_cuencas.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Resumen de sanciones por cuenca no encontrado.")

    if cuenca:
        data = [c for c in data if c.get("cuenca_codigo") == cuenca]
    return data


@app.get("/api/sma/sancion/{proceso_id}", tags=["Fiscalización Ambiental (SMA / SNIFA)"])
def obtener_detalle_sancion(proceso_id: str) -> Dict[str, Any]:
    """
    Obtiene el expediente detallado de un proceso sancionatorio específico de la SMA
    junto con sus instrumentos de fiscalización ambiental (RCA, NE 90/2000, D.S. 46/2002).
    """
    data = get_cached_json("sma_sanciones_agua_chile.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Dataset de sanciones SMA no encontrado.")

    for item in data:
        if str(item.get("proceso_sancion_id")) == str(proceso_id) or item.get("id") == proceso_id:
            return item

    raise HTTPException(status_code=404, detail=f"Proceso sancionatorio '{proceso_id}' no encontrado.")


# --- Catastro Público de Aguas (CPA / DAA - DGA Chile) ---

@app.get("/api/cpa/resumen-cuencas", tags=["Catastro Público de Aguas (CPA / DAA)"])
def resumen_cpa_cuencas(
    cuenca: Optional[str] = Query(None, description="Código DGA de la cuenca (ej. 057, 083, 034)")
) -> List[Dict[str, Any]]:
    """
    Retorna el balance volumétrico agregado del Catastro Público de Aguas (CPA) por macrocuenca:
    caudales totales otorgados (Consuntivos y No Consuntivos en L/s y m³/s), desglose superficial/subterráneo,
    permanente/eventual, principales titulares y derechos de mayor envergadura.
    """
    data = get_cached_json("cpa_resumen_cuencas.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Resumen de CPA por cuencas no encontrado.")

    if cuenca:
        data = [c for c in data if c.get("cuenca_codigo") == cuenca]
    return data


@app.get("/api/cpa/derechos", tags=["Catastro Público de Aguas (CPA / DAA)"])
def listar_derechos_cpa(
    cuenca: Optional[str] = Query(None, description="Código DGA de la cuenca (ej. 057, 083, 034)"),
    tipo: Optional[str] = Query(None, description="Tipo de derecho ('Consuntivo', 'No Consuntivo')"),
    naturaleza: Optional[str] = Query(None, description="Naturaleza del agua ('Superficial', 'Subterránea')"),
    ejercicio: Optional[str] = Query(None, description="Ejercicio del derecho ('Permanente', 'Eventual')"),
    titular: Optional[str] = Query(None, description="Filtro por nombre o razón social del titular"),
    min_lps: Optional[float] = Query(0.0, ge=0.0, description="Caudal mínimo otorgado en Litros por segundo (L/s)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """
    Retorna el listado paginado de derechos de aprovechamiento de aguas (DAA) estratégicos catastrados por la DGA,
    con filtros por cuenca, tipo, naturaleza del agua, régimen de ejercicio y caudal otorgado.
    """
    data = get_cached_json("cpa_derechos_destacados.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Dataset de derechos estratégicos CPA no encontrado.")

    if cuenca:
        data = [d for d in data if d.get("cuenca_codigo") == cuenca]
    if tipo:
        data = [d for d in data if tipo.lower() in (d.get("tipo_derecho") or "").lower()]
    if naturaleza:
        data = [d for d in data if naturaleza.lower() in (d.get("naturaleza_agua") or "").lower()]
    if ejercicio:
        data = [d for d in data if ejercicio.lower() in (d.get("ejercicio_derecho") or "").lower()]
    if titular:
        data = [d for d in data if titular.lower() in (d.get("titular") or "").lower()]
    if min_lps and min_lps > 0:
        data = [d for d in data if (d.get("caudal_concedido_lps") or 0.0) >= min_lps]

    total_filtrados = len(data)
    items = data[offset : offset + limit]
    return {
        "total_coincidentes": total_filtrados,
        "limit": limit,
        "offset": offset,
        "derechos": items
    }


@app.get("/api/cpa/derecho/{expediente}", tags=["Catastro Público de Aguas (CPA / DAA)"])
def obtener_detalle_derecho_cpa(expediente: str) -> Dict[str, Any]:
    """
    Obtiene el expediente oficial y la ficha técnica de un derecho de aprovechamiento de aguas (DAA)
    específico consignado en el Catastro Público de Aguas (CPA).
    """
    data = get_cached_json("cpa_derechos_destacados.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Dataset de derechos estratégicos CPA no encontrado.")

    exp_clean = expediente.strip().lower()
    for item in data:
        if (item.get("codigo_expediente") or "").strip().lower() == exp_clean or item.get("id") == expediente:
            return item

    raise HTTPException(status_code=404, detail=f"Derecho de aprovechamiento con expediente '{expediente}' no encontrado.")


# ==============================================================================
# SISS - Plantas de Tratamiento de Aguas Servidas (PTAS)
# ==============================================================================

@app.get("/api/siss/resumen-cuencas", tags=["Superintendencia de Servicios Sanitarios (SISS)"])
def resumen_siss_cuencas(
    cuenca: Optional[str] = Query(None, description="Código DGA de la cuenca (ej. 057, 083, 034)")
) -> List[Dict[str, Any]]:
    """
    Retorna el balance de descargas de aguas servidas tratadas (PTAS) por macrocuenca receptora,
    desglosado por cuerpos de agua receptores (Cauces Naturales Superficiales, Riego, Emisarios Submarinos).
    """
    data = get_cached_json("siss_resumen_cuencas.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Resumen de PTAS por cuencas no encontrado.")

    if cuenca:
        data = [c for c in data if c.get("cuenca_codigo") == cuenca]
    return data


    if cuenca:
        data = [c for c in data if c.get("cuenca_codigo") == cuenca]
    return data


@app.get("/api/siss/plantas", tags=["Superintendencia de Servicios Sanitarios (SISS)"])
def listar_plantas_siss(
    cuenca: Optional[str] = Query(None, description="Código DGA de la cuenca (ej. 057, 083)"),
    empresa: Optional[str] = Query(None, description="Filtro por empresa sanitaria (ej. Aguas Andinas, Esval, Essbio)"),
    tipo_receptor: Optional[str] = Query(None, description="Filtro por tipo de cuerpo receptor ('Cauce Natural', 'Riego', 'Marítimo')"),
    limit: int = Query(50, ge=1, le=300),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """
    Retorna el listado georreferenciado de Plantas de Tratamiento de Aguas Servidas (PTAS) y puntos de descarga
    regulados por la Superintendencia de Servicios Sanitarios (SISS).
    """
    data = get_cached_json("siss_plantas_chile.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Catastro de plantas SISS no encontrado.")

    if cuenca:
        data = [p for p in data if p.get("cuenca_codigo") == cuenca]
    if empresa:
        data = [p for p in data if empresa.lower() in (p.get("empresa_concesionaria") or "").lower()]
    if tipo_receptor:
        data = [p for p in data if tipo_receptor.lower() in (p.get("tipo_receptor") or "").lower() or tipo_receptor.lower() in (p.get("categoria_receptor") or "").lower()]

    total_filtrados = len(data)
    items = data[offset : offset + limit]
    return {
        "total_coincidentes": total_filtrados,
        "limit": limit,
        "offset": offset,
        "plantas": items
    }


@app.get("/api/siss/planta/{id_o_codigo}", tags=["Superintendencia de Servicios Sanitarios (SISS)"])
def obtener_detalle_planta_siss(id_o_codigo: str) -> Dict[str, Any]:
    """
    Retorna la ficha técnica de una Planta de Tratamiento de Aguas Servidas (PTAS) por ID o código de obra SISS.
    """
    data = get_cached_json("siss_plantas_chile.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Catastro de plantas SISS no encontrado.")

    target = id_o_codigo.strip().lower()
    for item in data:
        if (
            (item.get("id") or "").lower() == target
            or (str(item.get("codigo_obra") or "")).lower() == target
            or target in (item.get("nombre") or "").lower()
        ):
            return item

    raise HTTPException(status_code=404, detail=f"Planta de tratamiento '{id_o_codigo}' no encontrada.")


# ==============================================================================
# MMA - Humedales Urbanos Protegidos (Ley N° 21.202)
# ==============================================================================

@app.get("/api/mma/resumen-cuencas", tags=["Ministerio del Medio Ambiente (MMA) - Humedales Urbanos"])
def resumen_mma_cuencas(
    cuenca: Optional[str] = Query(None, description="Código DGA de la cuenca (ej. 057, 083, 104)")
) -> List[Dict[str, Any]]:
    """
    Retorna el balance de superficie de humedales urbanos declarados bajo la Ley N° 21.202
    agrupados por macrocuenca hidrográfica.
    """
    data = get_cached_json("mma_humedales_resumen_cuencas.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Resumen de humedales MMA por cuencas no encontrado.")

    if cuenca:
        data = [c for c in data if c.get("cuenca_codigo") == cuenca]
    return data


@app.get("/api/mma/humedales", tags=["Ministerio del Medio Ambiente (MMA) - Humedales Urbanos"])
def listar_humedales_mma(
    cuenca: Optional[str] = Query(None, description="Código DGA de la cuenca"),
    region: Optional[str] = Query(None, description="Filtro por región administrativa"),
    comuna: Optional[str] = Query(None, description="Filtro por comuna"),
    nombre: Optional[str] = Query(None, description="Filtro por nombre del humedal"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """
    Retorna el listado georreferenciado de Humedales Urbanos declarados bajo la Ley N° 21.202
    con su superficie protegida (hectáreas), decreto oficial y enlace al Diario Oficial / BCN.
    """
    data = get_cached_json("mma_humedales_chile.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Catastro de humedales MMA no encontrado.")

    if cuenca:
        data = [h for h in data if h.get("cuenca_codigo") == cuenca]
    if region:
        data = [h for h in data if region.lower() in (h.get("region") or "").lower()]
    if comuna:
        data = [h for h in data if comuna.lower() in (h.get("comuna") or "").lower()]
    if nombre:
        data = [h for h in data if nombre.lower() in (h.get("nombre") or "").lower()]

    total_filtrados = len(data)
    items = data[offset : offset + limit]
    return {
        "total_coincidentes": total_filtrados,
        "limit": limit,
        "offset": offset,
        "humedales": items
    }


@app.get("/api/mma/humedal/{codigo_o_id}", tags=["Ministerio del Medio Ambiente (MMA) - Humedales Urbanos"])
def obtener_detalle_humedal_mma(codigo_o_id: str) -> Dict[str, Any]:
    """
    Retorna la ficha oficial de un Humedal Urbano por código (ej. 'HU-0001') o ID.
    """
    data = get_cached_json("mma_humedales_chile.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Catastro de humedales MMA no encontrado.")

    target = codigo_o_id.strip().lower()
    for item in data:
        if (
            (item.get("id") or "").lower() == target
            or (item.get("codigo_humedal") or "").lower() == target
            or target in (item.get("nombre") or "").lower()
        ):
            return item

    raise HTTPException(status_code=404, detail=f"Humedal urbano '{codigo_o_id}' no encontrado.")


# ==============================================================================
# CNE / SEN - Centrales Hidroeléctricas en Operación
# ==============================================================================

@app.get("/api/cne/resumen-cuencas", tags=["Comisión Nacional de Energía (CNE) - Hidroelectricidad"])
def resumen_cne_cuencas(
    cuenca: Optional[str] = Query(None, description="Código DGA de la cuenca (ej. 083, 073, 104)")
) -> List[Dict[str, Any]]:
    """
    Retorna el balance de capacidad instalada hidroeléctrica (MW) por macrocuenca hidrográfica,
    desglosado por tecnología (Pasada vs. Embalse) y principales generadoras del SEN.
    """
    data = get_cached_json("cne_hidro_resumen_cuencas.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Balance de hidroelectricidad CNE por cuencas no encontrado.")

    if cuenca:
        data = [c for c in data if c.get("cuenca_codigo") == cuenca]
    return data


@app.get("/api/cne/hidroelectricas", tags=["Comisión Nacional de Energía (CNE) - Hidroelectricidad"])
def listar_centrales_cne(
    cuenca: Optional[str] = Query(None, description="Código DGA de la cuenca (ej. 083)"),
    tecnologia: Optional[str] = Query(None, description="Tecnología de generación ('Pasada', 'Embalse')"),
    propietario: Optional[str] = Query(None, description="Filtro por titular o empresa generadora (ej. Enel, Colbún, AES)"),
    min_mw: Optional[float] = Query(0.0, ge=0.0, description="Potencia mínima instalada en Megawatts (MW)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """
    Retorna el inventario georreferenciado de centrales hidroeléctricas en operación en el Sistema Eléctrico Nacional (SEN),
    con filtros por cuenca, tipo de tecnología hidráulica, titular y potencia en MW.
    """
    data = get_cached_json("cne_hidroelectricas_chile.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Catastro de hidroeléctricas CNE no encontrado.")

    if cuenca:
        data = [c for c in data if c.get("cuenca_codigo") == cuenca]
    if tecnologia:
        data = [c for c in data if tecnologia.lower() in (c.get("tipo_tecnologia") or "").lower()]
    if propietario:
        data = [c for c in data if propietario.lower() in (c.get("propietario") or "").lower()]
    if min_mw and min_mw > 0:
        data = [c for c in data if (c.get("potencia_mw") or 0.0) >= min_mw]

    total_filtrados = len(data)
    items = data[offset : offset + limit]
    return {
        "total_coincidentes": total_filtrados,
        "limit": limit,
        "offset": offset,
        "centrales": items
    }


@app.get("/api/cne/central/{id_o_nombre}", tags=["Comisión Nacional de Energía (CNE) - Hidroelectricidad"])
def obtener_detalle_central_cne(id_o_nombre: str) -> Dict[str, Any]:
    """
    Retorna la ficha técnica de una central hidroeléctrica por ID o nombre.
    """
    data = get_cached_json("cne_hidroelectricas_chile.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Catastro de hidroeléctricas CNE no encontrado.")

    target = id_o_nombre.strip().lower()
    for item in data:
        if (
            (item.get("id") or "").lower() == target
            or str(item.get("id_ge_hidro") or "").lower() == target
            or target in (item.get("nombre") or "").lower()
        ):
            return item

    raise HTTPException(status_code=404, detail=f"Central hidroeléctrica '{id_o_nombre}' no encontrada.")


# ==============================================================================
# SERNAGEOMIN - Catastro Nacional de Depósitos de Relaves Mineros (2025)
# ==============================================================================

@app.get("/api/relaves/resumen-cuencas", tags=["SERNAGEOMIN - Relaves Mineros"])
def resumen_relaves_cuencas(
    cuenca: Optional[str] = Query(None, description="Código DGA de la cuenca (ej. 045, 054, 057, 034)")
) -> List[Dict[str, Any]]:
    """
    Retorna el balance de depósitos de relaves mineros y pasivos ambientales por macrocuenca hidrográfica:
    total de depósitos, activos, inactivos, abandonados, volumen acumulado (millones de m³) y relaves de alto riesgo.
    """
    data = get_cached_json("sernageomin_relaves_resumen_cuencas.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Resumen de relaves SERNAGEOMIN no encontrado.")

    if cuenca:
        data = [c for c in data if c.get("cuenca_codigo") == cuenca]
    return data


    if cuenca:
        data = [c for c in data if c.get("cuenca_codigo") == cuenca]
    return data


@app.get("/api/relaves/depositos", tags=["SERNAGEOMIN - Relaves Mineros"])
def listar_relaves(
    cuenca: Optional[str] = Query(None, description="Código DGA de la cuenca"),
    estado: Optional[str] = Query(None, description="Estado operativo ('ACTIVO', 'ABANDONADO', 'INACTIVO')"),
    riesgo: Optional[str] = Query(None, description="Filtro de riesgo ('Crítico', 'Alto', 'Medio')"),
    titular: Optional[str] = Query(None, description="Filtro por titular minero o faena"),
    min_vol_m3: Optional[float] = Query(0.0, ge=0.0, description="Volumen mínimo actual en metros cúbicos"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """
    Retorna el catastro georreferenciado de depósitos de relaves mineros con filtros por cuenca,
    estado de la instalación, clasificación de riesgo ambiental y titular.
    """
    data = get_cached_json("sernageomin_relaves_chile.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Catastro de relaves SERNAGEOMIN no encontrado.")

    if cuenca:
        data = [r for r in data if r.get("cuenca_codigo") == cuenca]
    if estado:
        data = [r for r in data if estado.lower() in (r.get("estado_operativo") or "").lower()]
    if riesgo:
        data = [r for r in data if riesgo.lower() in (r.get("clasificacion_riesgo") or "").lower()]
    if titular:
        data = [r for r in data if titular.lower() in (r.get("titular_minero") or "").lower() or titular.lower() in (r.get("nombre_faena") or "").lower()]
    if min_vol_m3 and min_vol_m3 > 0:
        data = [r for r in data if (r.get("volumen_actual_m3") or 0.0) >= min_vol_m3]

    total_filtrados = len(data)
    items = data[offset : offset + limit]
    return {
        "total_coincidentes": total_filtrados,
        "limit": limit,
        "offset": offset,
        "relaves": items
    }


@app.get("/api/relaves/deposito/{id_o_codigo}", tags=["SERNAGEOMIN - Relaves Mineros"])
def obtener_detalle_relave(id_o_codigo: str) -> Dict[str, Any]:
    """
    Retorna la ficha técnica y de riesgo estructural de un depósito de relaves por ID o código SERNAGEOMIN.
    """
    data = get_cached_json("sernageomin_relaves_chile.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Catastro de relaves SERNAGEOMIN no encontrado.")

    target = id_o_codigo.strip().lower()
    for item in data:
        if (
            (item.get("id") or "").lower() == target
            or str(item.get("codigo_deposito") or "").lower() == target
            or target in (item.get("nombre_instalacion") or "").lower()
        ):
            return item

    raise HTTPException(status_code=404, detail=f"Depósito de relave '{id_o_codigo}' no encontrado.")


# ==============================================================================
# TGR / DGA - Patentes por No Uso de Aguas (Art. 129 bis Código de Aguas)
# ==============================================================================

@app.get("/api/patentes/resumen-cuencas", tags=["TGR / DGA - Patentes por No Uso"])
def resumen_patentes_cuencas(
    cuenca: Optional[str] = Query(None, description="Código DGA de la cuenca (ej. 057, 045, 083)")
) -> List[Dict[str, Any]]:
    """
    Retorna el balance de acaparamiento y especulación de derechos de agua por macrocuenca:
    total de patentes liquidadas, deuda acumulada en UTM y CLP, y porcentaje de morosidad.
    """
    data = get_cached_json("tgr_patentes_resumen_cuencas.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Resumen de patentes por cuencas no encontrado.")

    if cuenca:
        data = [c for c in data if c.get("cuenca_codigo") == cuenca]
    return data


@app.get("/api/patentes/morosos", tags=["TGR / DGA - Patentes por No Uso"])
def listar_patentes_morosas(
    cuenca: Optional[str] = Query(None, description="Código DGA de la cuenca"),
    comuna: Optional[str] = Query(None, description="Filtro por comuna"),
    rut: Optional[str] = Query(None, description="Filtro por RUT del titular"),
    min_utm: Optional[float] = Query(0.0, ge=0.0, description="Monto mínimo liquidado en UTM"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """
    Retorna la nómina de derechos de aprovechamiento afectos a pago de patente por no uso con saldo moroso.
    """
    data = get_cached_json("tgr_patentes_destacadas.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Nómina de patentes destacadas no encontrada.")

    if cuenca:
        data = [p for p in data if p.get("cuenca_codigo") == cuenca]
    if comuna:
        data = [p for p in data if comuna.lower() in (p.get("comuna") or "").lower()]
    if rut:
        data = [p for p in data if rut.lower() in (p.get("rut_rol_titular") or "").lower()]
    if min_utm and min_utm > 0:
        data = [p for p in data if (p.get("utm_liquidada") or 0.0) >= min_utm]

    total_filtrados = len(data)
    items = data[offset : offset + limit]
    return {
        "total_coincidentes": total_filtrados,
        "limit": limit,
        "offset": offset,
        "patentes": items
    }


@app.get("/api/patentes/patente/{cuenta_o_id}", tags=["TGR / DGA - Patentes por No Uso"])
def obtener_detalle_patente(cuenta_o_id: str) -> Dict[str, Any]:
    """
    Retorna la ficha de liquidación de una patente por no uso por número de cuenta TGR o ID.
    """
    data = get_cached_json("tgr_patentes_destacadas.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Nómina de patentes destacadas no encontrada.")

    target = cuenta_o_id.strip().lower()
    for item in data:
        if (
            (item.get("id") or "").lower() == target
            or str(item.get("cuenta_tgr") or "").lower() == target
            or str(item.get("folio") or "").lower() == target
        ):
            return item

    raise HTTPException(status_code=404, detail=f"Patente por no uso '{cuenta_o_id}' no encontrada.")


# ==============================================================================
# CONAF / SNASPE - Áreas Silvestres Protegidas del Estado
# ==============================================================================

@app.get("/api/snaspe/resumen-cuencas", tags=["CONAF / SNASPE - Reservas Hídricas"])
def resumen_snaspe_cuencas(
    cuenca: Optional[str] = Query(None, description="Código DGA de la cuenca (ej. 057, 101, 115)")
) -> List[Dict[str, Any]]:
    """
    Retorna el balance de superficie protegida (Parques Nacionales, Reservas y Monumentos)
    en las cabeceras de cada macrocuenca hidrográfica.
    """
    data = get_cached_json("conaf_snaspe_resumen_cuencas.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Resumen de SNASPE por cuencas no encontrado.")

    if cuenca:
        data = [c for c in data if c.get("cuenca_codigo") == cuenca]
    return data


@app.get("/api/snaspe/areas", tags=["CONAF / SNASPE - Reservas Hídricas"])
def listar_areas_snaspe(
    cuenca: Optional[str] = Query(None, description="Código DGA de la cuenca"),
    categoria: Optional[str] = Query(None, description="Categoría ('Parque Nacional', 'Reserva Nacional', 'Monumento Natural')"),
    region: Optional[str] = Query(None, description="Filtro por región"),
    nombre: Optional[str] = Query(None, description="Filtro por nombre de la unidad"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """
    Retorna el listado de unidades del SNASPE que protegen cabeceras de cuenca y reservas de agua.
    """
    data = get_cached_json("conaf_snaspe_chile.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Catastro de SNASPE no encontrado.")

    if cuenca:
        data = [a for a in data if a.get("cuenca_codigo") == cuenca]
    if categoria:
        data = [a for a in data if categoria.lower() in (a.get("categoria") or "").lower()]
    if region:
        data = [a for a in data if region.lower() in (a.get("region") or "").lower()]
    if nombre:
        data = [a for a in data if nombre.lower() in (a.get("nombre") or "").lower()]

    total_filtrados = len(data)
    items = data[offset : offset + limit]
    return {
        "total_coincidentes": total_filtrados,
        "limit": limit,
        "offset": offset,
        "areas_protegidas": items
    }


@app.get("/api/snaspe/area/{id_o_nombre}", tags=["CONAF / SNASPE - Reservas Hídricas"])
def obtener_detalle_area_snaspe(id_o_nombre: str) -> Dict[str, Any]:
    """
    Retorna la ficha técnica y legal de un Parque o Reserva Nacional del SNASPE.
    """
    data = get_cached_json("conaf_snaspe_chile.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Catastro de SNASPE no encontrado.")

    target = id_o_nombre.strip().lower()
    for item in data:
        if (
            (item.get("id") or "").lower() == target
            or target in (item.get("nombre") or "").lower()
            or target in (item.get("unidad") or "").lower()
        ):
            return item

    raise HTTPException(status_code=404, detail=f"Área protegida SNASPE '{id_o_nombre}' no encontrada.")



# ==============================================================================
# ACADES / MOP - Plantas Desalinizadoras de Agua de Mar
# ==============================================================================

@app.get("/api/desaladoras/resumen-cuencas", tags=["Plantas Desalinizadoras (Agua de Mar)"])
def resumen_desaladoras_cuencas(
    cuenca: Optional[str] = Query(None, description="Código DGA de la cuenca (ej. 023, 030, 044)")
) -> List[Dict[str, Any]]:
    """
    Retorna el balance de capacidad desaladora instalada (operativa y en proyecto)
    en L/s y m³/día agrupada por macrocuenca hidrográfica.
    """
    data = get_cached_json("desaladoras_resumen_cuencas.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Resumen de desaladoras por cuencas no encontrado.")

    if cuenca:
        data = [c for c in data if c.get("cuenca_codigo") == cuenca]
    return data


@app.get("/api/desaladoras/plantas", tags=["Plantas Desalinizadoras (Agua de Mar)"])
def listar_plantas_desaladoras(
    cuenca: Optional[str] = Query(None, description="Código DGA de la cuenca"),
    region: Optional[str] = Query(None, description="Filtro por región"),
    sector: Optional[str] = Query(None, description="Filtro por sector ('Minería', 'Agua Potable', 'Industrial', 'Multipropósito')"),
    estado: Optional[str] = Query(None, description="Filtro por estado ('En operación', 'EIA', 'En construcción', etc.)"),
    operativa_solo: Optional[bool] = Query(None, description="Si es True, sólo retorna plantas actualmente operativas"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """
    Retorna el catastro nacional de plantas desalinizadoras de agua de mar (ACADES / MOP).
    """
    data = get_cached_json("desaladoras_chile.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Catastro de plantas desalinizadoras no encontrado.")

    if cuenca:
        data = [p for p in data if p.get("cuenca_codigo") == cuenca]
    if region:
        data = [p for p in data if region.lower() in (p.get("region") or "").lower()]
    if sector:
        data = [p for p in data if sector.lower() in (p.get("sector_destino") or "").lower()]
    if estado:
        data = [p for p in data if estado.lower() in (p.get("estado_desarrollo") or "").lower()]
    if operativa_solo is not None:
        data = [p for p in data if p.get("es_operativa") == operativa_solo]

    total_filtrados = len(data)
    items = data[offset : offset + limit]
    return {
        "total_coincidentes": total_filtrados,
        "limit": limit,
        "offset": offset,
        "plantas_desalinizadoras": items
    }


@app.get("/api/desaladoras/planta/{id_o_nombre}", tags=["Plantas Desalinizadoras (Agua de Mar)"])
def obtener_detalle_planta_desaladora(id_o_nombre: str) -> Dict[str, Any]:
    """
    Retorna la ficha técnica, capacidad y coordenadas de una planta desalinizadora.
    """
    data = get_cached_json("desaladoras_chile.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Catastro de plantas desalinizadoras no encontrado.")

    target = id_o_nombre.strip().lower()
    for item in data:
        if (
            (item.get("id") or "").lower() == target
            or target in (item.get("nombre") or "").lower()
            or str(item.get("objectid") or "").lower() == target
        ):
            return item

    raise HTTPException(status_code=404, detail=f"Planta desalinizadora '{id_o_nombre}' no encontrada.")



# ==============================================================================
# Motor Analítico de Diagnóstico Holístico de Seguridad Hídrica por Cuenca (DDD)
# ==============================================================================

@app.get("/api/diagnostico/resumen", tags=["Diagnóstico Holístico de Seguridad Hídrica"])
def resumen_nacional_seguridad_hidrica() -> Dict[str, Any]:
    """
    Retorna el balance macro-ejecutivo de la seguridad hídrica de Chile:
    Índice ISH nacional promedio, distribución del semáforo regulatorio,
    top cuencas más críticas y sostenibles, y balance de reservas vs pasivos.
    """
    return diagnostic_service.obtener_resumen_nacional()


@app.get("/api/diagnostico/cuencas", tags=["Diagnóstico Holístico de Seguridad Hídrica"])
def ranking_diagnostico_cuencas(
    clasificacion: Optional[str] = Query(None, description="Filtro por semáforo ('CRÍTICO', 'VULNERABLE', 'SOSTENIBLE')"),
    region: Optional[str] = Query(None, description="Filtro por región"),
    zona: Optional[str] = Query(None, description="Filtro por zona hidrográfica ('Norte Grande', 'Norte Chico', 'Zona Central', 'Zona Sur', 'Zona Austral')"),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """
    Retorna el ranking nacional de cuencas ordenadas según el Índice de Seguridad Hídrica (ISH 0-100),
    con las macrocuencas más críticas en los primeros lugares.
    """
    todos = diagnostic_service.calcular_diagnostico_nacional()

    if clasificacion:
        todos = [c for c in todos if c.get("clasificacion") == clasificacion.upper()]
    if region:
        todos = [c for c in todos if region.lower() in (c.get("region") or "").lower()]
    if zona:
        todos = [c for c in todos if zona.lower() in (c.get("zona_hidrografica") or "").lower()]

    total_coincidentes = len(todos)
    items = todos[offset : offset + limit]

    return {
        "total_coincidentes": total_coincidentes,
        "limit": limit,
        "offset": offset,
        "cuencas": items
    }


@app.get("/api/diagnostico/cuenca/{codigo_dga}", tags=["Diagnóstico Holístico de Seguridad Hídrica"])
def diagnostico_ejecutivo_cuenca(codigo_dga: str) -> Dict[str, Any]:
    """
    Retorna la ficha ejecutiva de diagnóstico multidimensional para una cuenca DGA específica:
    - Índice de Seguridad Hídrica (0-100) y semáforo (CRÍTICO, VULNERABLE, SOSTENIBLE)
    - 5 Sub-índices analíticos (Disponibilidad, Ecosanitaria, Amenaza Antrópica, Humana APR, Gobernanza)
    - Métricas clave consolidadas de los 17 Bounded Contexts
    - Hallazgos críticos causales derivados del Knowledge Graph
    - Recomendaciones de gobernanza y política pública según legislación chilena
    """
    diag = diagnostic_service.calcular_diagnostico_cuenca(codigo_dga)
    if not diag:
        raise HTTPException(status_code=404, detail=f"Cuenca con código DGA '{codigo_dga}' no encontrada.")
    return diag


# ==============================================================================
# Clima, Meteorología y Megasequía (CR2MET / DMC / DGA)
# ==============================================================================

@app.get("/api/clima/resumen-cuencas", tags=["Clima, Meteorología y Megasequía"])
def resumen_clima_cuencas(
    cuenca: Optional[str] = Query(None, description="Código DGA de la cuenca (ej. 057, 045, 034)")
) -> List[Dict[str, Any]]:
    """
    Retorna el balance hidroclimático oficial (CR2MET / DMC / DGA) por macrocuenca:
    precipitación media anual (mm), evapotranspiración potencial, aridez, régimen,
    fracción nival, balance atmosférico y porcentaje de déficit de la Megasequía (2010-presente).
    """
    data = get_cached_json("clima_resumen_cuencas.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Resumen climático de cuencas no encontrado.")

    if cuenca:
        data = [c for c in data if c.get("cuenca_codigo") == cuenca]
    return data


@app.get("/api/clima/estaciones", tags=["Clima, Meteorología y Megasequía"])
def listar_estaciones_climaticas(
    cuenca: Optional[str] = Query(None, description="Código DGA de la cuenca"),
    regimen: Optional[str] = Query(None, description="Filtro por régimen ('Nival', 'Pluvio-Nival (Mixto)', 'Pluvial')"),
    clase_aridez: Optional[str] = Query(None, description="Filtro por clase de aridez ('Hiperárido', 'Árido', 'Semiárido', 'Subhúmedo Seco', 'Húmedo')"),
    nombre: Optional[str] = Query(None, description="Filtro por nombre de estación"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """
    Retorna el catálogo de estaciones hidroclimáticas y pluviométricas de Chile (CR2MET / DGA).
    """
    data = get_cached_json("clima_estaciones_chile.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Catastro de estaciones climáticas no encontrado.")

    if cuenca:
        data = [e for e in data if e.get("cuenca_codigo") == cuenca]
    if regimen:
        data = [e for e in data if regimen.lower() in (e.get("regimen_hidrologico") or "").lower()]
    if clase_aridez:
        data = [e for e in data if clase_aridez.lower() in (e.get("clasificacion_aridez") or "").lower()]
    if nombre:
        data = [e for e in data if nombre.lower() in (e.get("nombre") or "").lower()]

    total_filtrados = len(data)
    items = data[offset : offset + limit]
    return {
        "total_coincidentes": total_filtrados,
        "limit": limit,
        "offset": offset,
        "estaciones_climaticas": items
    }


@app.get("/api/clima/cuenca/{codigo_dga}", tags=["Clima, Meteorología y Megasequía"])
def obtener_clima_cuenca(codigo_dga: str) -> Dict[str, Any]:
    """
    Retorna la ficha hidroclimática completa para una macrocuenca específica:
    precipitación media anual, evapotranspiración, aridez, balance P - PET,
    impacto de megasequía, fracción nival y estaciones pluviométricas representativas.
    """
    data = get_cached_json("clima_resumen_cuencas.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Resumen climático no encontrado.")

    for item in data:
        if item.get("cuenca_codigo") == codigo_dga:
            return item

    raise HTTPException(status_code=404, detail=f"Ficha climática para la cuenca '{codigo_dga}' no encontrada.")



# ==============================================================================
# Ingesta Telemétrica Continua, Series de Tiempo y Tendencias (MEE / BNA)
# ==============================================================================

@app.post("/api/telemetria/lote", tags=["Telemetría en Vivo y MEE"])
def ingestar_lote_telemetrico(req: LoteTelemetricoRequest) -> Dict[str, Any]:
    """
    Ingesta un lote de mediciones telemétricas en tiempo real (bocatomas MEE, pozos de monitoreo,
    estaciones BNA o dataloggers de celadores), evalúa guardrails de extracción ilegal y
    persiste los registros en la capa de series temporales históricas.
    """
    if not req.lecturas:
        raise HTTPException(status_code=400, detail="El lote telemétrico no contiene lecturas.")

    # 1. Persistir lecturas en timeseries store
    ingestadas = timeseries_store.ingestar_lecturas(req.lecturas)

    # 2. Auditar guardrails de extracción ilegal si aplican
    alertas_infraccion = []
    for l in req.lecturas:
        if l.tipo_medicion == "CAUDAL_SUPERFICIAL_LPS":
            lectura_mee = LecturaSensorMEE(
                bocatoma_id=l.sensor_id,
                sensor_id=l.sensor_id,
                caudal_instantaneo_lps=l.valor,
                fecha_hora=l.fecha_hora
            )
            alerta = IllegalExtractionGuardrail.auditar_extraccion(
                lectura_mee=lectura_mee,
                ordenes_activas=req.ordenes_activas or []
            )
            if alerta:
                alertas_infraccion.append(alerta.model_dump())

    return {
        "status": "success",
        "total_lecturas_ingestadas": ingestadas,
        "total_alertas_infraccion": len(alertas_infraccion),
        "alertas_infraccion": alertas_infraccion
    }


@app.get("/api/telemetria/estacion/{sensor_id}/hidrograma", tags=["Telemetría en Vivo y MEE"])
def obtener_hidrograma_estacion(
    sensor_id: str,
    limite: int = Query(200, ge=1, le=2000, description="Límite máximo de puntos cronológicos"),
    horas_atras: Optional[int] = Query(None, ge=1, description="Ventana de tiempo en horas (ej. últimas 72h)")
) -> Dict[str, Any]:
    """
    Retorna la serie temporal histórica de caudales o niveles para construir el hidrograma de una estación.
    """
    puntos = timeseries_store.obtener_hidrograma(
        sensor_id=sensor_id,
        limite_puntos=limite,
        horas_atras=horas_atras
    )
    return {
        "sensor_id": sensor_id,
        "total_puntos": len(puntos),
        "serie_temporal": puntos
    }


@app.get("/api/telemetria/estacion/{sensor_id}/estadisticas", tags=["Telemetría en Vivo y MEE"])
def estadisticas_estacion_telemetrica(sensor_id: str) -> Dict[str, Any]:
    """
    Retorna estadísticas hidrológicas clave para un sensor: caudal medio, estiaje (Q5),
    crecida (Q95), valores máximos y mínimos registrados.
    """
    stats = timeseries_store.calcular_estadisticas_sensor(sensor_id)
    if "error" in stats:
        raise HTTPException(status_code=404, detail=stats["error"])
    return stats


@app.get("/api/telemetria/pozo/{sensor_id}/abatimiento", tags=["Telemetría en Vivo y MEE"])
def tendencia_abatimiento_pozo(sensor_id: str) -> Dict[str, Any]:
    """
    Analiza la tasa de abatimiento del nivel freático de un pozo subterráneo en un SHAC
    y determina si existe riesgo de sobreexplotación (Art. 63 Código de Aguas).
    """
    res = timeseries_store.analizar_abatimiento_pozo(sensor_id)
    return res.model_dump()


# ==============================================================================
# Sincronización Continua y Estado del Pipeline
# ==============================================================================

@app.get("/api/sync/ultimo-reporte", tags=["Sincronización Continua"])
def obtener_ultimo_reporte_sincronizacion() -> Dict[str, Any]:
    """
    Retorna los resultados del último ciclo de sincronización del gemelo digital:
    timestamp, número de nodos y aristas consolidadas, estado de decretos y tamaño del mapa.
    """
    report_file = DATA_DIR / "sync_report.json"
    if not report_file.exists():
        return {
            "estado": "PENDIENTE",
            "mensaje": "Aún no se ha ejecutado un ciclo de sincronización batch automatizado."
        }
    with open(report_file, "r", encoding="utf-8") as f:
        return json.load(f)


# ==============================================================================
# CONAF / KITRAL - Incendios Forestales y Degradación de Cabeceras
# ==============================================================================

@app.get("/api/incendios/resumen-cuencas", tags=["CONAF - Incendios y Cabeceras"])
def resumen_incendios_cuencas(
    cuenca: Optional[str] = Query(None, description="Código DGA de la macrocuenca (ej. 054, 057, 083)")
) -> List[Dict[str, Any]]:
    """
    Retorna el balance de incendios forestales catastróficos históricos, superficie total quemada (ha),
    y nivel de riesgo de colmatación y sedimentación de embalses por macrocuenca.
    """
    data = get_cached_json("conaf_incendios_resumen_cuencas.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Resumen de incendios por cuencas no encontrado.")

    if cuenca:
        data = [c for c in data if c.get("cuenca_codigo") == cuenca]
    return data


@app.get("/api/incendios/eventos", tags=["CONAF - Incendios y Cabeceras"])
def listar_eventos_incendios(
    cuenca: Optional[str] = Query(None, description="Código DGA de la cuenca"),
    temporada: Optional[str] = Query(None, description="Temporada del incendio (ej. '2023-2024')"),
    severidad: Optional[str] = Query(None, description="Severidad del incendio ('EXTREMA', 'MUY ALTA', 'ALTA')"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """
    Retorna los eventos y mega-incendios forestales con coordenadas, superficie calcinada (ha),
    amenaza a embalses aguas abajo y riesgo aluvial post-incendio.
    """
    data = get_cached_json("conaf_incendios_chile.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Catastro de incendios no encontrado.")

    if cuenca:
        data = [e for e in data if e.get("cuenca_codigo") == cuenca]
    if temporada:
        data = [e for e in data if temporada in (e.get("temporada") or "")]
    if severidad:
        data = [e for e in data if severidad.upper() in (e.get("severidad") or "").upper()]

    total_filtrados = len(data)
    items = data[offset : offset + limit]
    return {
        "total_coincidentes": total_filtrados,
        "limit": limit,
        "offset": offset,
        "incendios": items
    }


# ==============================================================================
# CNR / ODEPA - Demanda Agrícola y Eficiencia de Riego
# ==============================================================================

@app.get("/api/riego/resumen-cuencas", tags=["CNR / ODEPA - Demanda Agrícola y Riego"])
def resumen_riego_cuencas(
    cuenca: Optional[str] = Query(None, description="Código DGA de la macrocuenca (ej. 045, 057, 073)")
) -> List[Dict[str, Any]]:
    """
    Retorna el balance de demanda hídrica bruta agrícola (m³/año y L/s), superficie regada total,
    porcentaje de tecnificación (% goteo/aspersión vs gravitacional) y nivel de estrés hídrico agrícola.
    """
    data = get_cached_json("cnr_demanda_agricola_cuencas.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Resumen de demanda agrícola por cuencas no encontrado.")

    if cuenca:
        data = [c for c in data if c.get("cuenca_codigo") == cuenca]
    return data


@app.get("/api/riego/predios", tags=["CNR / ODEPA - Demanda Agrícola y Riego"])
def listar_distritos_riego(
    cuenca: Optional[str] = Query(None, description="Código DGA de la cuenca"),
    sistema_riego: Optional[str] = Query(None, description="Tipo de sistema ('Goteo Tecnificado', 'Gravitacional', 'Microaspersión')"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """
    Retorna distritos y valles de riego destacados en Chile con canal matriz fuente,
    superficie regada y eficiencia técnica de aplicación.
    """
    data = get_cached_json("cnr_riego_predios_destacados.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Catastro de predios y distritos de riego no encontrado.")

    if cuenca:
        data = [p for p in data if p.get("cuenca_codigo") == cuenca]
    if sistema_riego:
        data = [p for p in data if sistema_riego.lower() in (p.get("sistema_riego") or "").lower()]

    total_filtrados = len(data)
    items = data[offset : offset + limit]
    return {
        "total_coincidentes": total_filtrados,
        "limit": limit,
        "offset": offset,
        "distritos_riego": items
    }







