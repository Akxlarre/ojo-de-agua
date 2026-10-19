"""
Ingestor de Catastro Oficial Abierto de la DGA (Chile) para el Semantic Knowledge Graph.
Ingesta:
- SHACs (Sectores Hidrogeológicos de Aprovechamiento Común / Acuíferos)
- Red Hidrométrica Nacional (Estaciones Fluviométricas y Pozos BNA)
- Decretos de Escasez Hídrica (Art. 314)
- Zonas de Prohibición (Art. 63)
- Declaraciones de Agotamiento Superficial
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from src.memory.graph import DomainNode, DomainEdge
from src.harness.runner import KnowledgeHarness


class DGACatastroIngestReport(BaseModel):
    shacs_added: int = 0
    bna_stations_added: int = 0
    decrees_added: int = 0
    prohibitions_added: int = 0
    exhaustions_added: int = 0
    camels_added: int = 0
    ssr_added: int = 0
    glaciares_added: int = 0
    canales_added: int = 0
    sma_sanciones_added: int = 0
    cpa_derechos_added: int = 0
    siss_ptas_added: int = 0
    mma_humedales_added: int = 0
    cne_hidro_added: int = 0
    sernageomin_relaves_added: int = 0
    tgr_patentes_added: int = 0
    conaf_snaspe_added: int = 0
    desaladoras_added: int = 0
    incendios_added: int = 0
    riego_added: int = 0
    embalses_added: int = 0
    edges_added: int = 0



class DGACatastroIngestor:
    """
    Ingests official open data catalog files from DGA into the domain knowledge graph.
    """

    def __init__(self, harness: KnowledgeHarness, data_dir: Optional[str] = None):
        self.harness = harness
        if not data_dir:
            data_dir = str(Path(__file__).parent.parent.parent / "data")
        self.data_dir = Path(data_dir)

    def load_and_ingest(self) -> DGACatastroIngestReport:
        report = DGACatastroIngestReport()

        shac_path = self.data_dir / "shac_chile.json"
        bna_path = self.data_dir / "estaciones_bna_chile.json"
        dec_path = self.data_dir / "decretos_escasez_chile.json"
        zp_path = self.data_dir / "zonas_prohibicion_chile.json"
        agot_path = self.data_dir / "declaraciones_agotamiento_chile.json"

        # 1. SHACs
        if shac_path.exists():
            with open(shac_path, "r", encoding="utf-8") as f:
                shacs = json.load(f)
            for item in shacs:
                node_id = item['id']
                node = DomainNode(
                    id=node_id,
                    label="SHAC",
                    bounded_context="groundwater",
                    name=f"SHAC {item['nombre']}",
                    properties={
                        "codigo_shac": item['codigo_shac'],
                        "nombre": item['nombre'],
                        "acuifero": item['acuifero'],
                        "cuenca_asociada": item['cuenca_asociada'],
                        "codigo_cuenca_bna": item['codigo_cuenca_bna'],
                        "region": item['region'],
                        "area_km2": item['area_km2'],
                        "resolucion_dga": item['resolucion_dga'],
                        "centroide": item['centroide'],
                        "bbox": item['bbox']
                    }
                )
                self.harness.graph.add_node(node)
                report.shacs_added += 1

                # Relación con Cuenca si existe en el grafo
                c_bna = str(item.get('codigo_cuenca_bna') or "").strip()
                if c_bna:
                    c_id = f"cuenca-{c_bna.zfill(3)}"
                    if c_id in self.harness.graph.nodes:
                        edge = DomainEdge(
                            source_id=node_id,
                            target_id=c_id,
                            relation_type="SUBYACE_A",
                            bounded_context="topological",
                            properties={"tipo": "subterraneo_superficial"}
                        )
                        self.harness.graph.add_edge(edge)
                        report.edges_added += 1

        # 2. Estaciones BNA (Fluviométricas y de Pozos)
        if bna_path.exists():
            with open(bna_path, "r", encoding="utf-8") as f:
                stations = json.load(f)
            for item in stations:
                node_id = item['id']
                node = DomainNode(
                    id=node_id,
                    label="EstacionBNA",
                    bounded_context="telemetry",
                    name=f"Estación {item['nombre']}",
                    properties={
                        "codigo_bna": item['codigo_bna'],
                        "nombre": item['nombre'],
                        "tipo": item['tipo'],
                        "cuenca": item['cuenca'],
                        "codigo_cuenca": item['codigo_cuenca'],
                        "region": item['region'],
                        "comuna": item['comuna'],
                        "altitud_msnm": item['altitud_msnm'],
                        "parametros": item['parametros'],
                        "coordenadas": item['coordenadas']
                    }
                )
                self.harness.graph.add_node(node)
                report.bna_stations_added += 1

                c_cod = str(item.get('codigo_cuenca') or "").strip()
                if c_cod:
                    c_id = f"cuenca-{c_cod.zfill(3)}"
                    if c_id in self.harness.graph.nodes:
                        edge = DomainEdge(
                            source_id=node_id,
                            target_id=c_id,
                            relation_type="MONITOREA_EN",
                            bounded_context="telemetry",
                            properties={"tipo_estacion": item['tipo']}
                        )
                        self.harness.graph.add_edge(edge)
                        report.edges_added += 1

        # 3. Decretos de Escasez Hídrica
        if dec_path.exists():
            with open(dec_path, "r", encoding="utf-8") as f:
                decrees = json.load(f)
            for item in decrees:
                node_id = item['id']
                node = DomainNode(
                    id=node_id,
                    label="DecretoEscasez",
                    bounded_context="legal",
                    name=f"Decreto {item['decreto']} ({item['ano']})",
                    properties={
                        "decreto": item['decreto'],
                        "ano": item['ano'],
                        "region": item['region'],
                        "fecha_caducidad": item['fecha_caducidad'],
                        "cobertura": item['cobertura_territorial'],
                        "es_vigente": item['es_vigente']
                    }
                )
                self.harness.graph.add_node(node)
                report.decrees_added += 1

        # 4. Declaraciones de Agotamiento
        if agot_path.exists():
            with open(agot_path, "r", encoding="utf-8") as f:
                exhaustions = json.load(f)
            for item in exhaustions:
                node_id = item['id']
                node = DomainNode(
                    id=node_id,
                    label="DeclaracionAgotamiento",
                    bounded_context="legal",
                    name=f"Agotamiento {item['fuente_superficial']}",
                    properties={
                        "fuente": item['fuente_superficial'],
                        "region": item['region'],
                        "resolucion": item['resolucion_dga'],
                        "fecha": item['fecha_resolucion']
                    }
                )
                self.harness.graph.add_node(node)
                report.exhaustions_added += 1

        # 5. Zonas de Prohibición
        if zp_path.exists():
            with open(zp_path, "r", encoding="utf-8") as f:
                prohibitions = json.load(f)
            for item in prohibitions:
                node_id = item['id']
                node = DomainNode(
                    id=node_id,
                    label="ZonaProhibicion",
                    bounded_context="legal",
                    name=f"Prohibición {item['shac']}",
                    properties={
                        "shac": item['shac'],
                        "region": item['region'],
                        "resolucion": item['resolucion_dga'],
                        "fecha_res": item['fecha_resolucion']
                    }
                )
                self.harness.graph.add_node(node)
                report.prohibitions_added += 1

        # 6. CAMELS-CL (Atributos Hidroclimáticos de Cuencas)
        camels_path = self.data_dir / "camels_cl_cuencas.json"
        if camels_path.exists():
            with open(camels_path, "r", encoding="utf-8") as f:
                camels_data = json.load(f)
            for item in camels_data:
                node_id = item['id']
                nombre = item.get('nombre') or item.get('nombre_estacion') or str(item.get('codigo_bna', ''))
                node = DomainNode(
                    id=node_id,
                    label="CuencaCAMELS",
                    bounded_context="hydroclimate",
                    name=f"CAMELS {nombre}",
                    properties={
                        "codigo_bna": item.get('codigo_bna', ''),
                        "area_cuenca_km2": item.get('area_cuenca_km2', 0.0),
                        "elevacion_media_msnm": item.get('elevacion_media_msnm') or item.get('elevacion_msnm', 0.0),
                        "precipitacion_media_anual_mm": item.get('precipitacion_media_anual_mm', 0.0),
                        "evapotranspiracion_potencial_mm": item.get('evapotranspiracion_potencial_mm') or item.get('evapotranspiracion_potencial_anual_mm', 0.0),
                        "indice_aridez": item.get('indice_aridez', 0.0),
                        "caudal_medio_anual_m3s": item.get('caudal_medio_anual_m3s') or item.get('caudal_medio_m3s', 0.0),
                        "regimen_hidrologico": item.get('regimen_hidrologico', 'Pluvial'),
                        "deficit_megasequia_pct": item.get('deficit_megasequia_pct', 0.0),
                        "grado_intervencion_antropica": str(item.get('grado_intervencion_antropica', ''))
                    }
                )
                self.harness.graph.add_node(node)
                report.camels_added += 1

                # Relación con la estación BNA física si existe
                bna_id = f"bna_{item['codigo_bna']}"
                if bna_id in self.harness.graph.nodes:
                    edge = DomainEdge(
                        source_id=node_id,
                        target_id=bna_id,
                        relation_type="CARACTERIZA_AFORO",
                        bounded_context="hydroclimate",
                        properties={"intervencion": str(item.get('grado_intervencion_antropica', ''))}
                    )
                    self.harness.graph.add_edge(edge)
                    report.edges_added += 1

                # Relación con Macrocuenca DGA
                c_dga = item.get('cuenca_codigo') or (str(item.get('codigo_bna', '')).zfill(8)[:3] if len(str(item.get('codigo_bna', ''))) >= 3 else None)
                if c_dga:
                    c_id = f"cuenca-{str(c_dga).zfill(3)}"
                    if c_id in self.harness.graph.nodes:
                        edge = DomainEdge(
                            source_id=node_id,
                            target_id=c_id,
                            relation_type="MONITOREA_CLIMA_EN",
                            bounded_context="hydroclimate",
                            properties={
                                "precipitacion_media_anual_mm": item.get('precipitacion_media_anual_mm', 0.0),
                                "regimen_hidrologico": item.get('regimen_hidrologico', 'Pluvial')
                            }
                        )
                        self.harness.graph.add_edge(edge)
                        report.edges_added += 1

        # 7. Sistemas Sanitarios Rurales (SSR / APR)
        ssr_path = self.data_dir / "sistemas_ssr_apr_chile.json"
        if ssr_path.exists():
            with open(ssr_path, "r", encoding="utf-8") as f:
                ssr_data = json.load(f)
            for item in ssr_data:
                node_id = item['id']
                node = DomainNode(
                    id=node_id,
                    label="SistemaAPR",
                    bounded_context="drinking_water",
                    name=f"APR {item['nombre']}",
                    properties={
                        "codigo_ssr": item['codigo_ssr'],
                        "region": item['region'],
                        "provincia": item['provincia'],
                        "comuna": item['comuna'],
                        "cuenca_codigo": item.get('cuenca_codigo'),
                        "cuenca_nombre": item.get('cuenca_nombre'),
                        "arranques": item['arranques_domiciliarios'],
                        "beneficiarios": item['beneficiarios_estimados'],
                        "tipo_administracion": item['tipo_administracion'],
                        "coordenadas": item['coordenadas']
                    }
                )
                self.harness.graph.add_node(node)
                report.ssr_added += 1

                # Relación directa con la Macrocuenca DGA
                c_dga = item.get('cuenca_codigo')
                if c_dga:
                    c_id = f"cuenca-{str(c_dga).zfill(3)}"
                    if c_id in self.harness.graph.nodes:
                        edge = DomainEdge(
                            source_id=node_id,
                            target_id=c_id,
                            relation_type="ABASTECE_EN_CUENCA",
                            bounded_context="drinking_water",
                            properties={
                                "beneficiarios": item.get('beneficiarios_estimados', 0),
                                "arranques": item.get('arranques_domiciliarios', 0)
                            }
                        )
                        self.harness.graph.add_edge(edge)
                        report.edges_added += 1

        # 8. Inventario Público de Glaciares de Chile (IPG 2022)
        glaciares_path = self.data_dir / "glaciares_chile.json"
        if glaciares_path.exists():
            with open(glaciares_path, "r", encoding="utf-8") as f:
                glaciares_data = json.load(f)
            for item in glaciares_data:
                # Ingestar glaciares estratégicos (área >= 1.0 km² o con nombre oficial propio)
                if item.get("area_km2", 0) >= 1.0 or item.get("nombre_oficial"):
                    node_id = item["id"]
                    node = DomainNode(
                        id=node_id,
                        label="Glaciar",
                        bounded_context="cryosphere",
                        name=item["nombre"],
                        properties={
                            "codigo_glaciar": item["codigo_glaciar"],
                            "clasificacion": item["clasificacion"],
                            "area_km2": item["area_km2"],
                            "volumen_km3": item["volumen_km3"],
                            "equivalente_agua_km3": item["equivalente_agua_km3"],
                            "espesor_medio_m": item["espesor_medio_m"],
                            "elevacion_media_msnm": item["elevacion_media_msnm"],
                            "cuenca_codigo": item["cuenca_codigo"],
                            "region": item["region"],
                            "comuna": item["comuna"],
                            "coordenadas": item["coordenadas"],
                            "proteccion_legal": item["proteccion_legal"]
                        }
                    )
                    self.harness.graph.add_node(node)
                    report.glaciares_added += 1

                    # Relación topológica con la macrocuenca receptora
                    cuenca_id = f"cuenca-{item['cuenca_codigo']}"
                    if cuenca_id in self.harness.graph.nodes:
                        edge = DomainEdge(
                            source_id=node_id,
                            target_id=cuenca_id,
                            relation_type="ALIMENTA_CUENCA",
                            bounded_context="cryosphere",
                            properties={
                                "area_km2": item["area_km2"],
                                "equivalente_agua_km3": item["equivalente_agua_km3"]
                            }
                        )
                        self.harness.graph.add_edge(edge)
                        report.edges_added += 1

        # 9. Canales de Riego e Infraestructura Hídrica (CNR / CIREN)
        canales_path = self.data_dir / "canales_riego_chile.json"
        if canales_path.exists():
            with open(canales_path, "r", encoding="utf-8") as f:
                canales_data = json.load(f)
            for item in canales_data:
                # Ingestar canales matrices y de distribución estratégicos (longitud >= 5.0 km)
                if item.get("longitud_km", 0) >= 5.0:
                    node_id = f"canal_ciren_{item['codigo_canal']}"
                    node = DomainNode(
                        id=node_id,
                        label="Canal",
                        bounded_context="infrastructure",
                        name=item["nombre"],
                        properties={
                            "codigo_canal": item["codigo_canal"],
                            "tipo_canal": item["tipo_canal"],
                            "cuenca_codigo": item["cuenca_codigo"],
                            "fuente_hidrica": item["fuente_hidrica"],
                            "punto_origen": item["punto_origen"],
                            "longitud_km": item["longitud_km"],
                            "acciones_agua": item["acciones_agua"],
                            "porcentaje_revestimiento": item["porcentaje_revestimiento"],
                            "organizacion_usuarios": item["organizacion_usuarios"],
                            "junta_vigilancia": item["junta_vigilancia"],
                            "coordenadas_centroide": item["centroide"],
                            "coordenadas_inicio": item["coordenadas_inicio"]
                        }
                    )
                    self.harness.graph.add_node(node)
                    report.canales_added += 1

                    # Relación con la cuenca donde conduce aguas
                    cuenca_id = f"cuenca-{item['cuenca_codigo']}"
                    if cuenca_id in self.harness.graph.nodes:
                        edge = DomainEdge(
                            source_id=node_id,
                            target_id=cuenca_id,
                            relation_type="CONDUCE_EN_CUENCA",
                            bounded_context="infrastructure",
                            properties={
                                "longitud_km": item["longitud_km"],
                                "fuente": item["fuente_hidrica"]
                            }
                        )
                        self.harness.graph.add_edge(edge)
                        report.edges_added += 1

        # 10. Sanciones y Fiscalizaciones Ambientales de la SMA (Superintendencia del Medio Ambiente)
        sma_path = self.data_dir / "sma_sanciones_agua_chile.json"
        if sma_path.exists():
            with open(sma_path, "r", encoding="utf-8") as f:
                sma_data = json.load(f)
            for item in sma_data:
                # Ingestar sanciones estratégicas (relevantes para agua o multas significativas >= 50 UTA)
                if item.get("es_relevante_agua") or (item.get("multa_total_uta") or 0.0) >= 50.0:
                    node_id = item["id"]
                    node = DomainNode(
                        id=node_id,
                        label="SancionAmbiental",
                        bounded_context="environmental_compliance",
                        name=f"Sanción SMA {item['expediente']} ({item['unidad_fiscalizable_nombre']})",
                        properties={
                            "proceso_sancion_id": item["proceso_sancion_id"],
                            "expediente": item["expediente"],
                            "tipo_procedimiento": item["tipo_procedimiento"],
                            "estado": item["estado"],
                            "multa_total_uta": item["multa_total_uta"],
                            "unidad_fiscalizable_id": item["unidad_fiscalizable_id"],
                            "unidad_fiscalizable_nombre": item["unidad_fiscalizable_nombre"],
                            "categoria_economica": item["categoria_economica"],
                            "subcategoria_economica": item["subcategoria_economica"],
                            "region": item["region"],
                            "comuna": item["comuna"],
                            "cuenca_codigo": item["cuenca_codigo"],
                            "cuenca_nombre": item["cuenca_nombre"],
                            "link_snifa": item["link_snifa"],
                            "es_relevante_agua": item["es_relevante_agua"],
                            "etiquetas_hidricas": item["etiquetas_hidricas"],
                            "coordenadas": item["coordenadas"]
                        }
                    )
                    self.harness.graph.add_node(node)
                    report.sma_sanciones_added += 1

                    # Relación con la cuenca donde se cometió la infracción
                    cuenca_cod = item.get("cuenca_codigo")
                    if cuenca_cod:
                        cuenca_id = f"cuenca-{cuenca_cod}"
                        if cuenca_id in self.harness.graph.nodes:
                            edge = DomainEdge(
                                source_id=node_id,
                                target_id=cuenca_id,
                                relation_type="INFRINGE_EN_CUENCA",
                                bounded_context="environmental_compliance",
                                properties={
                                    "multa_uta": item["multa_total_uta"],
                                    "sector": item["categoria_economica"],
                                    "estado": item["estado"],
                                    "expediente": item["expediente"]
                                }
                            )
                            self.harness.graph.add_edge(edge)
                            report.edges_added += 1

        # 11. Catastro Público de Aguas (CPA / DAA) - Derechos de Aprovechamiento
        cpa_path = self.data_dir / "cpa_derechos_destacados.json"
        if cpa_path.exists():
            with open(cpa_path, "r", encoding="utf-8") as f:
                cpa_data = json.load(f)
            for item in cpa_data:
                # Ingestar títulos estratégicos de alto impacto hídrico
                caudal = item.get("caudal_concedido_lps") or 0.0
                tipo = item.get("tipo_derecho") or ""
                titular_low = (item.get("titular") or "").lower()
                is_selected = (
                    (tipo == "Consuntivo" and caudal >= 200.0) or
                    (tipo == "No Consuntivo" and caudal >= 5000.0) or
                    any(w in titular_low for w in ["aguas andinas", "esval", "essbio", "codelco", "collahuasi", "bhp", "enel", "colbun", "anglo"])
                )
                if is_selected:
                    node_id = item["id"]
                    node = DomainNode(
                        id=node_id,
                        label="DerechoAprovechamiento",
                        bounded_context="water_rights",
                        name=f"DAA {item['codigo_expediente']} ({item['titular'][:40]})",
                        properties={
                            "codigo_expediente": item["codigo_expediente"],
                            "solicitud_num": item["solicitud_num"],
                            "titular": item["titular"],
                            "tipo_derecho": item["tipo_derecho"],
                            "naturaleza_agua": item["naturaleza_agua"],
                            "ejercicio_derecho": item["ejercicio_derecho"],
                            "uso_agua": item["uso_agua"],
                            "caudal_concedido_lps": caudal,
                            "volumen_anual_m3": item.get("volumen_anual_m3"),
                            "fuente": item["fuente"],
                            "cuenca_codigo": item["cuenca_codigo"],
                            "cuenca_nombre": item["cuenca_nombre"],
                            "region": item["region"],
                            "comuna": item["comuna"],
                            "fecha_resolucion": item["fecha_resolucion"],
                            "numero_resolucion": item["numero_resolucion"],
                            "coordenadas": item.get("coordenadas")
                        }
                    )
                    self.harness.graph.add_node(node)
                    report.cpa_derechos_added += 1

                    # Relación con la cuenca hidrográfica otorgante
                    cuenca_cod = item.get("cuenca_codigo")
                    if cuenca_cod:
                        cuenca_id = f"cuenca-{cuenca_cod}"
                        if cuenca_id in self.harness.graph.nodes:
                            edge = DomainEdge(
                                source_id=node_id,
                                target_id=cuenca_id,
                                relation_type="CONCEDIDO_EN_CUENCA",
                                bounded_context="water_rights",
                                properties={
                                    "caudal_lps": caudal,
                                    "tipo": tipo,
                                    "naturaleza": item["naturaleza_agua"],
                                    "titular": item["titular"]
                                }
                            )
                            self.harness.graph.add_edge(edge)
                            report.edges_added += 1
        # 12. Plantas de Tratamiento de Aguas Servidas (SISS - Superintendencia de Servicios Sanitarios)
        siss_path = self.data_dir / "siss_plantas_chile.json"
        if siss_path.exists():
            with open(siss_path, "r", encoding="utf-8") as f:
                siss_data = json.load(f)
            for item in siss_data:
                node_id = item["id"]
                node = DomainNode(
                    id=node_id,
                    label="PlantaTratamiento",
                    bounded_context="sanitation",
                    name=f"PTAS {item['nombre']} ({item['empresa_concesionaria']})",
                    properties={
                        "codigo_obra": item["codigo_obra"],
                        "nombre": item["nombre"],
                        "empresa_concesionaria": item["empresa_concesionaria"],
                        "rut_empresa": item["rut_empresa"],
                        "sistema_urbano": item["sistema_urbano"],
                        "ano_construccion": item["ano_construccion"],
                        "estado_operativo": item["estado_operativo"],
                        "cuerpo_receptor": item["cuerpo_receptor"],
                        "tipo_receptor": item["tipo_receptor"],
                        "categoria_receptor": item["categoria_receptor"],
                        "region": item["region"],
                        "cuenca_codigo": item["cuenca_codigo"],
                        "cuenca_nombre": item["cuenca_nombre"],
                        "coordenadas": item.get("coordenadas")
                    }
                )
                self.harness.graph.add_node(node)
                report.siss_ptas_added += 1

                # Relación de descarga a la cuenca hidrográfica receptora
                cuenca_cod = item.get("cuenca_codigo")
                if cuenca_cod:
                    cuenca_id = f"cuenca-{cuenca_cod}"
                    if cuenca_id in self.harness.graph.nodes:
                        edge = DomainEdge(
                            source_id=node_id,
                            target_id=cuenca_id,
                            relation_type="DESCARGA_EN_CUENCA",
                            bounded_context="sanitation",
                            properties={
                                "receptor": item["cuerpo_receptor"],
                                "tipo_receptor": item["tipo_receptor"],
                                "empresa": item["empresa_concesionaria"]
                            }
                        )
                        self.harness.graph.add_edge(edge)
                        report.edges_added += 1

        # 13. Inventario Nacional de Humedales Urbanos Protegidos (MMA - Ley N° 21.202)
        mma_path = self.data_dir / "mma_humedales_chile.json"
        if mma_path.exists():
            with open(mma_path, "r", encoding="utf-8") as f:
                mma_data = json.load(f)
            for item in mma_data:
                node_id = item["id"]
                node = DomainNode(
                    id=node_id,
                    label="HumedalUrbano",
                    bounded_context="ecosystems",
                    name=f"Humedal Urbano {item['nombre']}",
                    properties={
                        "codigo_humedal": item["codigo_humedal"],
                        "nombre": item["nombre"],
                        "superficie_ha": item["superficie_ha"],
                        "superficie_km2": item["superficie_km2"],
                        "region": item["region"],
                        "comuna": item["comuna"],
                        "tipo_declaratoria": item["tipo_declaratoria"],
                        "resolucion_mma": item["resolucion_mma"],
                        "enlace_decreto_bcn": item["enlace_decreto_bcn"],
                        "enlace_simbio": item["enlace_simbio"],
                        "cuenca_codigo": item["cuenca_codigo"],
                        "cuenca_nombre": item["cuenca_nombre"],
                        "coordenadas": item.get("coordenadas"),
                        "es_protegido_ley_21202": item["es_protegido_ley_21202"]
                    }
                )
                self.harness.graph.add_node(node)
                report.mma_humedales_added += 1

                # Relación con la cuenca hidrográfica de conservación
                cuenca_cod = item.get("cuenca_codigo")
                if cuenca_cod:
                    cuenca_id = f"cuenca-{cuenca_cod}"
                    if cuenca_id in self.harness.graph.nodes:
                        edge = DomainEdge(
                            source_id=node_id,
                            target_id=cuenca_id,
                            relation_type="PROTEGIDO_EN_CUENCA",
                            bounded_context="ecosystems",
                            properties={
                                "superficie_ha": item["superficie_ha"],
                                "resolucion": item["resolucion_mma"]
                            }
                        )
                        self.harness.graph.add_edge(edge)
                        report.edges_added += 1

        # 14. Catastro de Centrales Hidroeléctricas en Operación (CNE / SEN)
        cne_path = self.data_dir / "cne_hidroelectricas_chile.json"
        if cne_path.exists():
            with open(cne_path, "r", encoding="utf-8") as f:
                cne_data = json.load(f)
            for item in cne_data:
                node_id = item["id"]
                node = DomainNode(
                    id=node_id,
                    label="CentralHidroelectrica",
                    bounded_context="energy",
                    name=f"Central {item['nombre']} ({item['potencia_mw']} MW)",
                    properties={
                        "id_ge_hidro": item["id_ge_hidro"],
                        "nombre": item["nombre"],
                        "propietario": item["propietario"],
                        "tipo_tecnologia": item["tipo_tecnologia"],
                        "potencia_mw": item["potencia_mw"],
                        "unidades_generacion": item["unidades_generacion"],
                        "sistema_electrico": item["sistema_electrico"],
                        "estado_operativo": item["estado_operativo"],
                        "resolucion_calificacion_ambiental": item.get("resolucion_calificacion_ambiental"),
                        "region": item["region"],
                        "cuenca_codigo": item["cuenca_codigo"],
                        "cuenca_nombre": item["cuenca_nombre"],
                        "coordenadas": item.get("coordenadas"),
                        "fuente_oficial": item["fuente_oficial"]
                    }
                )
                self.harness.graph.add_node(node)
                report.cne_hidro_added += 1

                # Relación de generación hidroeléctrica en la cuenca
                cuenca_cod = item.get("cuenca_codigo")
                if cuenca_cod:
                    cuenca_id = f"cuenca-{cuenca_cod}"
                    if cuenca_id in self.harness.graph.nodes:
                        edge = DomainEdge(
                            source_id=node_id,
                            target_id=cuenca_id,
                            relation_type="TURBINA_EN_CUENCA",
                            bounded_context="energy",
                            properties={
                                "potencia_mw": item["potencia_mw"],
                                "tipo_tecnologia": item["tipo_tecnologia"],
                                "propietario": item["propietario"]
                            }
                        )
                        self.harness.graph.add_edge(edge)
                        report.edges_added += 1

        # 15. Catastro Nacional de Depósitos de Relaves Mineros (SERNAGEOMIN 2025)
        relaves_path = self.data_dir / "sernageomin_relaves_chile.json"
        if relaves_path.exists():
            with open(relaves_path, "r", encoding="utf-8") as f:
                relaves_data = json.load(f)
            for item in relaves_data:
                node_id = item["id"]
                node = DomainNode(
                    id=node_id,
                    label="DepositoRelave",
                    bounded_context="mining_risk",
                    name=f"Relave {item['nombre_instalacion']} ({item['titular_minero'][:35]})",
                    properties={
                        "codigo_deposito": item["codigo_deposito"],
                        "nombre_faena": item["nombre_faena"],
                        "nombre_instalacion": item["nombre_instalacion"],
                        "titular_minero": item["titular_minero"],
                        "rut_titular": item.get("rut_titular"),
                        "tipo_deposito": item["tipo_deposito"],
                        "recurso_mineral": item["recurso_mineral"],
                        "estado_operativo": item["estado_operativo"],
                        "metodo_constructivo_muro": item["metodo_constructivo_muro"],
                        "clasificacion_riesgo": item["clasificacion_riesgo"],
                        "volumen_actual_m3": item["volumen_actual_m3"],
                        "tonelaje_actual": item["tonelaje_actual"],
                        "region": item["region"],
                        "comuna": item["comuna"],
                        "cuenca_codigo": item["cuenca_codigo"],
                        "cuenca_nombre": item["cuenca_nombre"],
                        "coordenadas": item.get("coordenadas"),
                        "fuente_oficial": item["fuente_oficial"]
                    }
                )
                self.harness.graph.add_node(node)
                report.sernageomin_relaves_added += 1

                # Relación topológica de amenaza de pasivo o riesgo sobre la cuenca receptora
                cuenca_cod = item.get("cuenca_codigo")
                if cuenca_cod:
                    cuenca_id = f"cuenca-{cuenca_cod}"
                    if cuenca_id in self.harness.graph.nodes:
                        edge = DomainEdge(
                            source_id=node_id,
                            target_id=cuenca_id,
                            relation_type="AMENAZA_CUENCA",
                            bounded_context="mining_risk",
                            properties={
                                "estado": item["estado_operativo"],
                                "riesgo": item["clasificacion_riesgo"],
                                "volumen_m3": item["volumen_actual_m3"],
                                "metodo": item["metodo_constructivo_muro"]
                            }
                        )
                        self.harness.graph.add_edge(edge)
                        report.edges_added += 1

        # 16. Nómina Oficial de Patentes por No Uso de Aguas (TGR / DGA - Art. 129 bis)
        patentes_path = self.data_dir / "tgr_patentes_destacadas.json"
        if patentes_path.exists():
            with open(patentes_path, "r", encoding="utf-8") as f:
                patentes_data = json.load(f)
            for item in patentes_data:
                # Ingestar títulos estratégicos con alta morosidad o significancia (UTM >= 50 o saldo >= $3.000.000)
                if item.get("utm_liquidada", 0) >= 50.0 or item.get("saldo_deuda_clp", 0) >= 3_000_000.0:
                    node_id = item["id"]
                    node = DomainNode(
                        id=node_id,
                        label="PatenteNoUso",
                        bounded_context="water_rights_enforcement",
                        name=f"Patente No Uso {item['cuenta_tgr']} ({item['utm_liquidada']} UTM)",
                        properties={
                            "cuenta_tgr": item["cuenta_tgr"],
                            "folio": item["folio"],
                            "rut_rol_titular": item["rut_rol_titular"],
                            "tipo_persona": item["tipo_persona"],
                            "monto_liquidado_clp": item["monto_liquidado_clp"],
                            "saldo_deuda_clp": item["saldo_deuda_clp"],
                            "monto_pagado_clp": item["monto_pagado_clp"],
                            "utm_liquidada": item["utm_liquidada"],
                            "ano_patente": item["ano_patente"],
                            "comuna": item["comuna"],
                            "tesoreria_regional": item["tesoreria_regional"],
                            "cuenca_codigo": item["cuenca_codigo"],
                            "cuenca_nombre": item["cuenca_nombre"],
                            "es_moroso": item["es_moroso"]
                        }
                    )
                    self.harness.graph.add_node(node)
                    report.tgr_patentes_added += 1

                    # Relación con la cuenca donde se acaparan derechos sin uso
                    cuenca_cod = item.get("cuenca_codigo")
                    if cuenca_cod:
                        cuenca_id = f"cuenca-{cuenca_cod}"
                        if cuenca_id in self.harness.graph.nodes:
                            edge = DomainEdge(
                                source_id=node_id,
                                target_id=cuenca_id,
                                relation_type="AFECTA_DERECHO_EN_CUENCA",
                                bounded_context="water_rights_enforcement",
                                properties={
                                    "utm": item["utm_liquidada"],
                                    "saldo_clp": item["saldo_deuda_clp"],
                                    "ano": item["ano_patente"]
                                }
                            )
                            self.harness.graph.add_edge(edge)
                            report.edges_added += 1

        # 17. Sistema Nacional de Áreas Silvestres Protegidas del Estado (CONAF / SNASPE)
        snaspe_path = self.data_dir / "conaf_snaspe_chile.json"
        if snaspe_path.exists():
            with open(snaspe_path, "r", encoding="utf-8") as f:
                snaspe_data = json.load(f)
            for item in snaspe_data:
                node_id = item["id"]
                node = DomainNode(
                    id=node_id,
                    label="AreaSilvestreProtegida",
                    bounded_context="ecosystems_preservation",
                    name=f"{item['nombre']} ({item['superficie_ha']} ha)",
                    properties={
                        "id_catastro": item["id_catastro"],
                        "nombre": item["nombre"],
                        "unidad": item["unidad"],
                        "categoria": item["categoria"],
                        "region": item["region"],
                        "superficie_ha": item["superficie_ha"],
                        "superficie_km2": item["superficie_km2"],
                        "decreto_creacion": item["decreto_creacion"],
                        "cuenca_codigo": item["cuenca_codigo"],
                        "cuenca_nombre": item["cuenca_nombre"],
                        "coordenadas_centroide": item.get("coordenadas_centroide"),
                        "es_reserva_cabecera": item["es_reserva_cabecera"],
                        "fuente_oficial": item["fuente_oficial"]
                    }
                )
                self.harness.graph.add_node(node)
                report.conaf_snaspe_added += 1

                # Relación de protección hidrológica de cabecera en la cuenca
                cuenca_cod = item.get("cuenca_codigo")
                if cuenca_cod:
                    cuenca_id = f"cuenca-{cuenca_cod}"
                    if cuenca_id in self.harness.graph.nodes:
                        edge = DomainEdge(
                            source_id=node_id,
                            target_id=cuenca_id,
                            relation_type="PROTEGE_CABECERA_CUENCA",
                            bounded_context="ecosystems_preservation",
                            properties={
                                "categoria": item["categoria"],
                                "superficie_ha": item["superficie_ha"],
                                "decreto": item["decreto_creacion"]
                            }
                        )
                        self.harness.graph.add_edge(edge)
                        report.edges_added += 1

        # 18. Catastro Nacional de Plantas Desaladoras (ACADES / MOP)
        desal_path = self.data_dir / "desaladoras_chile.json"
        if desal_path.exists():
            with open(desal_path, "r", encoding="utf-8") as f:
                desal_data = json.load(f)
            for item in desal_data:
                node_id = item["id"]
                node = DomainNode(
                    id=node_id,
                    label="PlantaDesaladora",
                    bounded_context="desalination",
                    name=f"Desaladora {item['nombre']} ({item['capacidad_lps']} L/s)",
                    properties={
                        "nombre": item["nombre"],
                        "operador": item["operador"],
                        "sector_destino": item["sector_destino"],
                        "estado_operativo": item["estado_operativo"],
                        "es_operativa": item["es_operativa"],
                        "tecnologia": item["tecnologia"],
                        "capacidad_lps": item["capacidad_lps"],
                        "capacidad_m3_dia": item["capacidad_m3_dia"],
                        "region": item["region"],
                        "cuenca_codigo": item["cuenca_codigo"],
                        "cuenca_nombre": item["cuenca_nombre"],
                        "coordenadas": item.get("coordenadas"),
                        "fuente_oficial": item["fuente_oficial"]
                    }
                )
                self.harness.graph.add_node(node)
                report.desaladoras_added += 1

                # Relación con la cuenca costera beneficiada
                cuenca_cod = item.get("cuenca_codigo")
                if cuenca_cod:
                    cuenca_id = f"cuenca-{cuenca_cod}"
                    if cuenca_id in self.harness.graph.nodes:
                        edge = DomainEdge(
                            source_id=node_id,
                            target_id=cuenca_id,
                            relation_type="ABASTECE_CUENCA",
                            bounded_context="desalination",
                            properties={
                                "capacidad_lps": item["capacidad_lps"],
                                "sector": item["sector_destino"],
                                "es_operativa": item["es_operativa"]
                            }
                        )
                        self.harness.graph.add_edge(edge)
                        report.edges_added += 1

        # 19. Incendios Forestales y Degradación de Cuencas (CONAF / KITRAL)
        incendios_path = self.data_dir / "conaf_incendios_chile.json"
        if incendios_path.exists():
            with open(incendios_path, "r", encoding="utf-8") as f:
                incendios_data = json.load(f)
            for item in incendios_data:
                node_id = item["id"]
                node = DomainNode(
                    id=node_id,
                    label="IncendioForestal",
                    bounded_context="wildfire_risk",
                    name=f"Incendio {item['nombre']} ({item['superficie_ha']} ha)",
                    properties={
                        "nombre": item["nombre"],
                        "temporada": item["temporada"],
                        "fecha_inicio": item["fecha_inicio"],
                        "comuna": item["comuna"],
                        "region": item["region"],
                        "cuenca_codigo": item["cuenca_codigo"],
                        "superficie_ha": item["superficie_ha"],
                        "severidad": item["severidad"],
                        "impacto_embalse": item.get("impacto_embalse"),
                        "riesgo_aluvial_post_incendio": item.get("riesgo_aluvial_post_incendio"),
                        "coordenadas": [item["latitud"], item["longitud"]]
                    }
                )
                self.harness.graph.add_node(node)
                report.incendios_added += 1

                # Relación de degradación de cabecera con la cuenca
                cuenca_cod = item.get("cuenca_codigo")
                if cuenca_cod:
                    cuenca_id = f"cuenca-{cuenca_cod}"
                    if cuenca_id in self.harness.graph.nodes:
                        edge = DomainEdge(
                            source_id=node_id,
                            target_id=cuenca_id,
                            relation_type="DEGRADA_CABECERA",
                            bounded_context="wildfire_risk",
                            properties={
                                "superficie_ha": item["superficie_ha"],
                                "severidad": item["severidad"]
                            }
                        )
                        self.harness.graph.add_edge(edge)
                        report.edges_added += 1

        # 20. Demanda Agrícola y Eficiencia de Riego (CNR / ODEPA)
        riego_path = self.data_dir / "cnr_demanda_agricola_cuencas.json"
        if riego_path.exists():
            with open(riego_path, "r", encoding="utf-8") as f:
                riego_data = json.load(f)
            for item in riego_data:
                node_id = f"demanda_agricola_{item['cuenca_codigo']}"
                node = DomainNode(
                    id=node_id,
                    label="DemandaAgricola",
                    bounded_context="agricultural_demand",
                    name=f"Demanda Agrícola Cuenca {item['cuenca_codigo']} ({item['demanda_media_agricola_lps']} L/s)",
                    properties={
                        "cuenca_codigo": item["cuenca_codigo"],
                        "cuenca_nombre": item["cuenca_nombre"],
                        "superficie_regada_total_ha": item["superficie_regada_total_ha"],
                        "superficie_riego_tecnificado_ha": item["superficie_riego_tecnificado_ha"],
                        "porcentaje_tecnificacion": item["porcentaje_tecnificacion"],
                        "demanda_hidrica_bruta_m3_ano": item["demanda_hidrica_bruta_m3_ano"],
                        "demanda_media_agricola_lps": item["demanda_media_agricola_lps"],
                        "estres_hidrico_agricola": item["estres_hidrico_agricola"],
                        "cultivos_principales": item["cultivos_principales"],
                        "fuente_oficial": item["fuente_oficial"]
                    }
                )
                self.harness.graph.add_node(node)
                report.riego_added += 1

                # Relación de extracción hídrica con la cuenca
                cuenca_id = f"cuenca-{item['cuenca_codigo']}"
                if cuenca_id in self.harness.graph.nodes:
                    edge = DomainEdge(
                        source_id=node_id,
                        target_id=cuenca_id,
                        relation_type="EXTRAE_DE_CUENCA",
                        bounded_context="agricultural_demand",
                        properties={
                            "demanda_lps": item["demanda_media_agricola_lps"],
                            "estres": item["estres_hidrico_agricola"],
                            "tecnificacion_pct": item["porcentaje_tecnificacion"]
                        }
                    )
                    self.harness.graph.add_edge(edge)
                    report.edges_added += 1

        # Predios / Sectores de riego destacados
        predios_path = self.data_dir / "cnr_riego_predios_destacados.json"
        if predios_path.exists():
            with open(predios_path, "r", encoding="utf-8") as f:
                predios_data = json.load(f)
            for item in predios_data:
                node_id = item["id"]
                node = DomainNode(
                    id=node_id,
                    label="PredioRiego",
                    bounded_context="agricultural_demand",
                    name=f"Valle Riego: {item['nombre_valle']}",
                    properties=item
                )
                self.harness.graph.add_node(node)
                report.riego_added += 1

                cuenca_id = f"cuenca-{item['cuenca_codigo']}"
                if cuenca_id in self.harness.graph.nodes:
                    edge = DomainEdge(
                        source_id=node_id,
                        target_id=cuenca_id,
                        relation_type="UBICADO_EN_CUENCA",
                        bounded_context="agricultural_demand",
                        properties={
                            "superficie_ha": item["superficie_ha"],
                            "sistema_riego": item["sistema_riego"]
                        }
                    )
                    self.harness.graph.add_edge(edge)
                    report.edges_added += 1

        # 21. Catastro Oficial de Embalses Estratégicos (DGA / DOH)
        emb_path = self.data_dir / "embalses_oficiales_chile.json"
        cuencas_path = self.data_dir / "cuencas_dga_chile.json"
        cuencas_list = []
        if cuencas_path.exists():
            with open(cuencas_path, "r", encoding="utf-8") as f:
                cuencas_list = json.load(f)

        if emb_path.exists():
            with open(emb_path, "r", encoding="utf-8") as f:
                emb_data = json.load(f)
            for item in emb_data:
                if item.get("monitoreo_dga") or item.get("tamano") == "GRANDE":
                    coords = item.get("coordenadas")
                    c_cod = None
                    if coords and len(coords) == 2:
                        lat, lon = coords[0], coords[1]
                        for c in cuencas_list:
                            b = c.get("bbox")
                            if b and b.get("lat_min", -99) <= lat <= b.get("lat_max", 99) and b.get("lon_min", -99) <= lon <= b.get("lon_max", 99):
                                c_cod = c.get("codigo_dga")
                                break

                    node_id = item["id"]
                    node = DomainNode(
                        id=node_id,
                        label="Embalse",
                        bounded_context="infrastructure",
                        name=f"Embalse {item['nombre']}",
                        properties={
                            "nombre": item["nombre"],
                            "region": item.get("region"),
                            "comuna": item.get("comuna"),
                            "altura_muro_m": item.get("altura_muro_m"),
                            "uso": item.get("uso"),
                            "tamano": item.get("tamano"),
                            "ano_construccion": item.get("ano_construccion"),
                            "monitoreo_dga": item.get("monitoreo_dga"),
                            "coordenadas": coords,
                            "cuenca_codigo": c_cod
                        }
                    )
                    self.harness.graph.add_node(node)
                    report.embalses_added += 1

                    if c_cod:
                        cuenca_id = f"cuenca-{c_cod}"
                        if cuenca_id in self.harness.graph.nodes:
                            edge = DomainEdge(
                                source_id=node_id,
                                target_id=cuenca_id,
                                relation_type="REGULA_CUENCA",
                                bounded_context="infrastructure",
                                properties={
                                    "uso": item.get("uso"),
                                    "altura_muro_m": item.get("altura_muro_m")
                                }
                            )
                            self.harness.graph.add_edge(edge)
                            report.edges_added += 1

        return report

