"""
Motor de Relaciones Causales e Interoperabilidad Semántica de Segundo Orden (DDD).
Genera aristas complejas directas entre entidades del dominio:
1. DepositoRelave --[AMENAZA_AGUAS_ARRIBA]--> SistemaAPR
2. PlantaTratamiento --[DESCARGA_SOBRE_HUMEDAL]--> HumedalUrbano
3. CentralHidroelectrica --[COMPITE_CON_RIEGO]--> JuntaVigilancia
4. PlantaDesaladora --[ALIVIA_PRESION_HÍDRICA]--> Cuenca
5. IncendioForestal --[AMENAZA_DEGRADACION_CABECERA]--> Embalse
6. DemandaAgricola --[COMPITE_POR_RECURSO_CON_APR]--> SistemaAPR
"""

import math
from collections import defaultdict
from typing import Any, Dict, List, Tuple
from src.memory.graph import DomainEdge, DomainKnowledgeGraph


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula la distancia geográfica en kilómetros entre dos coordenadas WGS84."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(r * c, 2)


class CrossDomainRelationBuilder:
    """
    Construye las conexiones causales de segundo orden entre entidades del Knowledge Graph.
    """

    def __init__(self, graph: DomainKnowledgeGraph):
        self.graph = graph

    def build_all_cross_relations(self) -> Dict[str, int]:
        report = {
            "amenaza_relave_apr_added": 0,
            "descarga_ptas_humedal_added": 0,
            "compite_hidro_riego_added": 0,
            "alivio_desalacion_added": 0,
            "amenaza_incendio_embalse_added": 0,
            "compite_agricola_apr_added": 0
        }

        nodes = self.graph.nodes

        relaves = [n for n in nodes.values() if n.label == "DepositoRelave"]
        aprs = [n for n in nodes.values() if n.label == "SistemaAPR"]
        ptas_list = [n for n in nodes.values() if n.label == "PlantaTratamiento"]
        humedales = [n for n in nodes.values() if n.label == "HumedalUrbano"]
        hidros = [n for n in nodes.values() if n.label == "CentralHidroelectrica"]
        juntas = [n for n in nodes.values() if n.label == "JuntaVigilancia"]
        desaladoras = [n for n in nodes.values() if n.label == "PlantaDesaladora"]

        # 1. AMENAZA_AGUAS_ARRIBA: Relaves críticos/abandonados a menos de 20 km de un Sistema APR
        aprs_by_region = defaultdict(list)
        for a in aprs:
            reg = (a.properties.get("region") or "").strip().lower()
            coords = a.properties.get("coordenadas")
            if coords and len(coords) == 2 and coords[0] != 0:
                aprs_by_region[reg].append((a, coords[0], coords[1]))

        for r in relaves:
            r_coords = r.properties.get("coordenadas")
            is_risky = r.properties.get("estado_operativo") == "ABANDONADO" or "Crítico" in (r.properties.get("clasificacion_riesgo") or "") or "Alto" in (r.properties.get("clasificacion_riesgo") or "")
            if not is_risky or not r_coords:
                continue

            r_lat = r_coords.get("latitud")
            r_lon = r_coords.get("longitud")
            r_reg = (r.properties.get("region") or "").strip().lower()
            if not r_lat or not r_lon:
                continue

            nearby_aprs = []
            for reg, alist in aprs_by_region.items():
                if reg in r_reg or r_reg in reg or not reg or not r_reg:
                    for a, a_lat, a_lon in alist:
                        dist = haversine_km(r_lat, r_lon, a_lat, a_lon)
                        if dist <= 20.0:
                            nearby_aprs.append((dist, a))

            nearby_aprs.sort(key=lambda x: x[0])
            for dist, a in nearby_aprs[:3]:  # Top 3 APRs más vulnerables al depósito
                edge = DomainEdge(
                    source_id=r.id,
                    target_id=a.id,
                    relation_type="AMENAZA_AGUAS_ARRIBA",
                    bounded_context="mining_risk",
                    properties={
                        "distancia_km": dist,
                        "riesgo_relave": r.properties.get("clasificacion_riesgo"),
                        "estado_relave": r.properties.get("estado_operativo"),
                        "beneficiarios_apr": a.properties.get("beneficiarios")
                    }
                )
                self.graph.add_edge(edge)
                report["amenaza_relave_apr_added"] += 1

        # 2. DESCARGA_SOBRE_HUMEDAL: PTAS y Humedales en la misma cuenca a menos de 25 km
        humedales_by_cuenca = defaultdict(list)
        for h in humedales:
            c = h.properties.get("cuenca_codigo")
            coords = h.properties.get("coordenadas")
            if coords and coords.get("latitud"):
                humedales_by_cuenca[c].append((h, coords["latitud"], coords["longitud"]))

        for p in ptas_list:
            p_cuenca = p.properties.get("cuenca_codigo")
            p_coords = p.properties.get("coordenadas")
            if not p_coords or not p_coords.get("latitud"):
                continue

            p_lat = p_coords["latitud"]
            p_lon = p_coords["longitud"]
            candidates = humedales_by_cuenca.get(p_cuenca, [])

            for h, h_lat, h_lon in candidates:
                dist = haversine_km(p_lat, p_lon, h_lat, h_lon)
                if dist <= 25.0:
                    edge = DomainEdge(
                        source_id=p.id,
                        target_id=h.id,
                        relation_type="DESCARGA_PROXIMA_HUMEDAL",
                        bounded_context="environmental_compliance",
                        properties={
                            "distancia_km": dist,
                            "cuerpo_receptor": p.properties.get("cuerpo_receptor"),
                            "superficie_ha_humedal": h.properties.get("superficie_ha")
                        }
                    )
                    self.graph.add_edge(edge)
                    report["descarga_ptas_humedal_added"] += 1

        # 3. COMPITE_CON_RIEGO: Centrales Hidroeléctricas (> 20 MW o Embalse) en la misma cuenca que Juntas de Vigilancia
        juntas_by_cuenca = defaultdict(list)
        for j in juntas:
            c = j.properties.get("cuenca_codigo")
            if c:
                juntas_by_cuenca[c].append(j)

        for ch in hidros:
            c_cod = ch.properties.get("cuenca_codigo")
            mw = float(ch.properties.get("potencia_mw") or 0.0)
            tipo = ch.properties.get("tipo_tecnologia") or ""
            if mw >= 20.0 or tipo == "Embalse":
                for j in juntas_by_cuenca.get(c_cod, []):
                    edge = DomainEdge(
                        source_id=ch.id,
                        target_id=j.id,
                        relation_type="COMPITE_CON_RIEGO",
                        bounded_context="energy",
                        properties={
                            "potencia_mw": mw,
                            "tipo_hidro": tipo,
                            "conflicto_tipo": "Regulacion estival vs Despacho SEN"
                        }
                    )
                    self.graph.add_edge(edge)
                    report["compite_hidro_riego_added"] += 1

        # 4. ALIVIA_PRESION_HÍDRICA: Desaladoras conectadas a las cuencas DGA
        for d in desaladoras:
            c_cod = d.properties.get("cuenca_codigo")
            if c_cod:
                c_id = f"cuenca-{c_cod}"
                if c_id in self.graph.nodes:
                    edge = DomainEdge(
                        source_id=d.id,
                        target_id=c_id,
                        relation_type="ALIVIA_PRESION_HIDRICA",
                        bounded_context="desalination",
                        properties={
                            "capacidad_lps": d.properties.get("capacidad_lps"),
                            "sector": d.properties.get("sector_destino"),
                            "es_operativa": d.properties.get("es_operativa")
                        }
                    )
                    self.graph.add_edge(edge)
                    report["alivio_desalacion_added"] += 1

        # 5. AMENAZA_DEGRADACION_CABECERA: Incendios Forestales severos sobre Embalses Estratégicos
        embalses = [n for n in nodes.values() if n.label == "Embalse"]
        incendios = [n for n in nodes.values() if n.label == "IncendioForestal"]
        for inc in incendios:
            inc_cuenca = inc.properties.get("cuenca_codigo")
            inc_coords = inc.properties.get("coordenadas")
            inc_sev = inc.properties.get("severidad")
            for emb in embalses:
                emb_cuenca = emb.properties.get("cuenca_codigo")
                emb_coords = emb.properties.get("coordenadas")
                is_same_cuenca = bool(inc_cuenca and emb_cuenca and inc_cuenca == emb_cuenca)
                dist = None
                if inc_coords and emb_coords and len(inc_coords) == 2 and len(emb_coords) == 2:
                    dist = haversine_km(inc_coords[0], inc_coords[1], emb_coords[0], emb_coords[1])

                if is_same_cuenca or (dist is not None and dist <= 40.0):
                    edge = DomainEdge(
                        source_id=inc.id,
                        target_id=emb.id,
                        relation_type="AMENAZA_DEGRADACION_CABECERA",
                        bounded_context="wildfire_risk",
                        properties={
                            "severidad_incendio": inc_sev,
                            "superficie_ha": inc.properties.get("superficie_ha"),
                            "distancia_km": dist if dist is not None else 0.0,
                            "impacto_embalse": inc.properties.get("impacto_embalse") or "Sedimentación y pérdida de capacidad de regulación",
                            "riesgo_aluvial": inc.properties.get("riesgo_aluvial_post_incendio")
                        }
                    )
                    self.graph.add_edge(edge)
                    report["amenaza_incendio_embalse_added"] += 1

        # 6. COMPITE_POR_RECURSO_CON_APR: Demanda Agrícola en cuencas de alto/crítico estrés sobre Sistemas APR rurales
        demandas = [n for n in nodes.values() if n.label == "DemandaAgricola"]
        aprs_by_cuenca = defaultdict(list)
        for a in aprs:
            c = a.properties.get("cuenca_codigo")
            if c:
                aprs_by_cuenca[c].append(a)

        for dem in demandas:
            estres = dem.properties.get("estres_hidrico_agricola")
            if estres in ["CRÍTICO", "MUY ALTO", "ALTO"]:
                c_cod = dem.properties.get("cuenca_codigo")
                cuenca_aprs = aprs_by_cuenca.get(c_cod, [])
                # Relacionar con los APRs con mayor número de beneficiarios en la cuenca (top 3)
                cuenca_aprs_sorted = sorted(
                    cuenca_aprs,
                    key=lambda x: int(x.properties.get("beneficiarios") or x.properties.get("arranques") or 0),
                    reverse=True
                )
                for apr_node in cuenca_aprs_sorted[:3]:
                    edge = DomainEdge(
                        source_id=dem.id,
                        target_id=apr_node.id,
                        relation_type="COMPITE_POR_RECURSO_CON_APR",
                        bounded_context="agricultural_demand",
                        properties={
                            "estres_agricola": estres,
                            "demanda_lps": dem.properties.get("demanda_media_agricola_lps"),
                            "tecnificacion_pct": dem.properties.get("porcentaje_tecnificacion"),
                            "beneficiarios_apr": apr_node.properties.get("beneficiarios")
                        }
                    )
                    self.graph.add_edge(edge)
                    report["compite_agricola_apr_added"] += 1

        return report
