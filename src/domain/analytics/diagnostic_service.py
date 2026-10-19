"""
Motor Analítico de Diagnóstico Holístico de Seguridad Hídrica por Cuenca (DDD).
Cruza los 17 Bounded Contexts y las 4 familias de aristas causales del Knowledge Graph:
1. DepositoRelave --[AMENAZA_AGUAS_ARRIBA]--> SistemaAPR
2. PlantaTratamiento --[DESCARGA_PROXIMA_HUMEDAL]--> HumedalUrbano
3. CentralHidroelectrica --[COMPITE_CON_RIEGO]--> JuntaVigilancia
4. PlantaDesaladora --[ALIVIA_PRESION_HIDRICA]--> Cuenca

Calcula el Índice de Seguridad Hídrica (ISH 0-100), semáforo regulatorio y
recomendaciones de política pública según la legislación chilena (DFL 1.122, Ley 21.435,
Ley 21.202, D.S. 90 y Art. 129 bis).
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections import defaultdict, Counter


class HolisticCuencaDiagnosticService:
    """
    Servicio de analítica multidimensional que evalúa la salud, vulnerabilidad
    y gobernanza hídrica de cada macrocuenca hidrográfica de Chile.
    """

    def __init__(self, data_dir: Optional[Path] = None, graph_data: Optional[Dict[str, Any]] = None):
        self.data_dir = data_dir or (Path(__file__).parent.parent.parent.parent / "data")
        self.graph_data = graph_data
        self._load_datasets()
        self._load_graph_data()

    def _load_json(self, filename: str) -> Any:
        path = self.data_dir / filename
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _load_datasets(self):
        # 1. Base Cuencas
        self.cuencas_raw = self._load_json("cuencas_dga_chile.json")
        self.cuencas_dict = {c.get("codigo_dga"): c for c in self.cuencas_raw if c.get("codigo_dga")}

        # 2. CPA Derechos de Agua
        cpa_list = self._load_json("cpa_resumen_cuencas.json")
        self.cpa_dict = {c.get("cuenca_codigo"): c for c in cpa_list if c.get("cuenca_codigo")}

        # 3. Glaciares
        glac_list = self._load_json("glaciares_resumen_cuencas.json")
        self.glaciares_dict = {c.get("cuenca_codigo"): c for c in glac_list if c.get("cuenca_codigo")}

        # 4. Relaves Sernageomin
        rel_list = self._load_json("sernageomin_relaves_resumen_cuencas.json")
        self.relaves_dict = {c.get("cuenca_codigo"): c for c in rel_list if c.get("cuenca_codigo")}

        # 5. Patentes No Uso TGR
        tgr_list = self._load_json("tgr_patentes_resumen_cuencas.json")
        self.tgr_dict = {c.get("cuenca_codigo"): c for c in tgr_list if c.get("cuenca_codigo")}

        # 6. Desaladoras ACADES
        desal_list = self._load_json("desaladoras_resumen_cuencas.json")
        self.desal_dict = {c.get("cuenca_codigo"): c for c in desal_list if c.get("cuenca_codigo")}

        # 7. SISS Sanitarias (PTAS / PTAP)
        siss_list = self._load_json("siss_resumen_cuencas.json")
        self.siss_dict = {c.get("cuenca_codigo"): c for c in siss_list if c.get("cuenca_codigo")}

        # 8. Humedales Urbanos MMA
        hum_list = self._load_json("mma_humedales_resumen_cuencas.json")
        self.humedales_dict = {c.get("cuenca_codigo"): c for c in hum_list if c.get("cuenca_codigo")}

        # 9. SNASPE CONAF
        snaspe_list = self._load_json("conaf_snaspe_resumen_cuencas.json")
        self.snaspe_dict = {c.get("cuenca_codigo"): c for c in snaspe_list if c.get("cuenca_codigo")}

        # 10. CNE Hidroeléctricas
        cne_list = self._load_json("cne_hidro_resumen_cuencas.json")
        self.cne_dict = {c.get("cuenca_codigo"): c for c in cne_list if c.get("cuenca_codigo")}

        # 11. CAMELS-CL Hidrología
        camels_list = self._load_json("camels_cl_cuencas.json")
        self.camels_dict = {c.get("cuenca_codigo"): c for c in camels_list if c.get("cuenca_codigo")}

        # 12. SMA Sanciones
        sma_list = self._load_json("sma_resumen_cuencas.json")
        self.sma_dict = {c.get("cuenca_codigo"): c for c in sma_list if c.get("cuenca_codigo")}

        # 13. Decretos de Escasez y Agotamiento
        self.escasez_raw = self._load_json("decretos_escasez_chile.json")
        self.agotamiento_raw = self._load_json("declaraciones_agotamiento_chile.json")

        # 14. APR / SSR
        apr_raw = self._load_json("sistemas_ssr_apr_chile.json")
        self.apr_by_cuenca = defaultdict(list)
        for a in apr_raw:
            c = a.get("cuenca_codigo")
            if c:
                self.apr_by_cuenca[c].append(a)

        # 15. Organizaciones de Usuarios (OUAs)
        ouas_raw = self._load_json("registro_nacional_ouas.json")
        self.ouas_by_cuenca = defaultdict(list)
        for o in ouas_raw:
            c = o.get("cuenca_codigo")
            if c:
                self.ouas_by_cuenca[c].append(o)

        # 16. Clima y Megasequía (CR2MET / DMC / DGA)
        clima_list = self._load_json("clima_resumen_cuencas.json")
        self.clima_dict = {c.get("cuenca_codigo"): c for c in clima_list if c.get("cuenca_codigo")}

        # 17. Incendios Forestales y Degradación de Cabeceras (CONAF / KITRAL)
        incendios_list = self._load_json("conaf_incendios_resumen_cuencas.json")
        self.incendios_dict = {c.get("cuenca_codigo"): c for c in incendios_list if c.get("cuenca_codigo")}

        # 18. Demanda Agrícola y Eficiencia de Riego (CNR / ODEPA)
        riego_list = self._load_json("cnr_demanda_agricola_cuencas.json")
        self.riego_dict = {c.get("cuenca_codigo"): c for c in riego_list if c.get("cuenca_codigo")}

    def _load_graph_data(self):
        """
        Carga nodos y aristas causales del Knowledge Graph para indexar
        las relaciones causales directas por cuenca hidrográfica.
        """
        self.causal_edges_count = defaultdict(lambda: defaultdict(int))
        graph_file = self.data_dir / "knowledge_graph_chile.json"

        nodes = {}
        edges = []

        if self.graph_data:
            raw_nodes = self.graph_data.get("nodes", [])
            if isinstance(raw_nodes, dict):
                nodes = raw_nodes
            else:
                nodes = {n.get("id"): n for n in raw_nodes if n.get("id")}
            edges = self.graph_data.get("edges", [])
        elif graph_file.exists():
            try:
                with open(graph_file, "r", encoding="utf-8") as f:
                    g = json.load(f)
                    raw_nodes = g.get("nodes", [])
                    if isinstance(raw_nodes, dict):
                        nodes = raw_nodes
                    else:
                        nodes = {n.get("id"): n for n in raw_nodes if n.get("id")}
                    edges = g.get("edges", [])
            except Exception:
                nodes = {}
                edges = []

        self.graph_nodes = nodes

        # Indexar aristas causales directas por cuenca
        for e in edges:
            rel = e.get("relation_type")
            src_id = e.get("source_id")
            tgt_id = e.get("target_id")

            src_node = nodes.get(src_id)
            tgt_node = nodes.get(tgt_id)

            if rel == "AMENAZA_AGUAS_ARRIBA":
                # Origen es un relave con cuenca_codigo
                if src_node:
                    cod = src_node.get("properties", {}).get("cuenca_codigo")
                    if cod:
                        self.causal_edges_count[cod]["amenaza_relave_apr"] += 1

            elif rel == "DESCARGA_PROXIMA_HUMEDAL":
                # Origen es una PTAS con cuenca_codigo
                if src_node:
                    cod = src_node.get("properties", {}).get("cuenca_codigo")
                    if cod:
                        self.causal_edges_count[cod]["descarga_ptas_humedal"] += 1

            elif rel == "COMPITE_CON_RIEGO":
                # Origen es una central hidroeléctrica con cuenca_codigo
                if src_node:
                    cod = src_node.get("properties", {}).get("cuenca_codigo")
                    if cod:
                        self.causal_edges_count[cod]["compite_hidro_riego"] += 1

            elif rel == "ALIVIA_PRESION_HIDRICA":
                # Destino es cuenca-{cod} o origen es desaladora
                if tgt_id and tgt_id.startswith("cuenca-"):
                    cod = tgt_id.replace("cuenca-", "")
                    self.causal_edges_count[cod]["alivio_desalacion"] += 1
                elif src_node:
                    cod = src_node.get("properties", {}).get("cuenca_codigo")
                    if cod:
                        self.causal_edges_count[cod]["alivio_desalacion"] += 1

            elif rel == "AMENAZA_DEGRADACION_CABECERA":
                # Origen es un IncendioForestal con cuenca_codigo
                if src_node:
                    cod = src_node.get("properties", {}).get("cuenca_codigo")
                    if cod:
                        self.causal_edges_count[cod]["amenaza_incendio_embalse"] += 1

            elif rel == "COMPITE_POR_RECURSO_CON_APR":
                # Origen es DemandaAgricola con cuenca_codigo
                if src_node:
                    cod = src_node.get("properties", {}).get("cuenca_codigo")
                    if cod:
                        self.causal_edges_count[cod]["compite_agricola_apr"] += 1

    def calcular_diagnostico_cuenca(self, codigo_dga: str) -> Optional[Dict[str, Any]]:
        """
        Calcula el diagnóstico holístico e ISH para una cuenca específica.
        """
        base = self.cuencas_dict.get(codigo_dga)
        if not base:
            return None

        nombre = base.get("nombre", f"Cuenca {codigo_dga}")
        region = base.get("region", "Chile")
        zona = base.get("zona_hidrografica", "Zona Central")
        area_km2 = float(base.get("superficie_km2") or 1000.0)

        # Contextual metrics
        cpa = self.cpa_dict.get(codigo_dga, {})
        glac = self.glaciares_dict.get(codigo_dga, {})
        rel = self.relaves_dict.get(codigo_dga, {})
        tgr = self.tgr_dict.get(codigo_dga, {})
        desal = self.desal_dict.get(codigo_dga, {})
        siss = self.siss_dict.get(codigo_dga, {})
        hum = self.humedales_dict.get(codigo_dga, {})
        snaspe = self.snaspe_dict.get(codigo_dga, {})
        cne = self.cne_dict.get(codigo_dga, {})
        camels = self.camels_dict.get(codigo_dga, {})
        sma = self.sma_dict.get(codigo_dga, {})

        aprs = self.apr_by_cuenca.get(codigo_dga, [])
        ouas = self.ouas_by_cuenca.get(codigo_dga, [])

        # Values
        cpa_consuntivo_lps = float(cpa.get("caudal_consuntivo_total_lps") or 0.0)
        cpa_derechos_total = int(cpa.get("total_derechos") or 0)

        glac_count = int(glac.get("glaciares_count") or glac.get("total_glaciares") or 0)
        glac_area_km2 = float(glac.get("superficie_total_km2") or 0.0)
        glac_vol_km3 = float(glac.get("volumen_total_km3") or glac.get("volumen_hielo_km3") or 0.0)
        glac_agua_km3 = float(glac.get("equivalente_agua_total_km3") or (glac_vol_km3 * 0.85))

        relaves_total = int(rel.get("total_relaves") or 0)
        relaves_abandonados = int(rel.get("relaves_abandonados") or 0)
        relaves_activos = int(rel.get("relaves_activos") or 0)
        relaves_vol_m3 = float(rel.get("volumen_total_actual_m3") or 0.0)

        patentes_no_uso_count = int(tgr.get("total_patentes_no_uso") or 0)
        patentes_deuda_utm = float(tgr.get("deuda_total_utm") or 0.0)
        patentes_deuda_clp = float(tgr.get("monto_total_clp") or 0.0)

        desal_operativa_lps = float(desal.get("capacidad_operacion_lps") or 0.0)
        desal_total_plantas = int(desal.get("total_desaladoras") or 0)

        ptas_count = int(siss.get("total_ptas") or 0)
        ptap_count = int(siss.get("total_ptap") or 0)

        humedales_count = int(hum.get("total_humedales") or 0)
        humedales_ha = float(hum.get("superficie_total_ha") or 0.0)

        snaspe_count = int(snaspe.get("total_areas_protegidas") or 0)
        snaspe_ha = float(snaspe.get("superficie_total_ha") or 0.0)

        cne_hidro_mw = float(cne.get("potencia_total_mw") or 0.0)

        sma_sanciones_count = int(sma.get("total_sanciones") or 0)

        apr_count = len(aprs)
        apr_beneficiarios = sum(int(a.get("beneficiarios_estimados") or a.get("beneficiarios") or (int(a.get("arranques_domiciliarios") or a.get("arranques") or 0) * 3) or 0) for a in aprs)

        jv_count = sum(1 for o in ouas if "vigilancia" in (o.get("tipo") or o.get("nombre") or "").lower())
        total_ouas = len(ouas)

        # Clima y Megasequía (CR2MET / DMC)
        clima = self.clima_dict.get(codigo_dga, {})
        p_anual_mm = float(clima.get("precipitacion_media_anual_mm") or 500.0)
        pet_anual_mm = float(clima.get("evapotranspiracion_potencial_mm") or 1000.0)
        aridez_idx = float(clima.get("indice_aridez_medio") or 1.5)
        balance_atm_mm = float(clima.get("balance_hidrico_atmosferico_mm") or (p_anual_mm - pet_anual_mm))
        deficit_megasequia = float(clima.get("deficit_megasequia_pct") or 20.0)
        fraccion_nival = float(clima.get("fraccion_nival_media_pct") or 10.0)
        regimen_hidro = str(clima.get("regimen_hidrologico_predominante") or "Pluvial")
        estaciones_meteo_total = int(clima.get("total_estaciones_cr2met") or 0) + int(clima.get("total_estaciones_meteo_dga") or 0)

        # Incendios Forestales (CONAF / KITRAL)
        inc = self.incendios_dict.get(codigo_dga, {})
        inc_eventos = int(inc.get("total_incendios_registrados") or 0)
        inc_sup_ha = float(inc.get("superficie_total_quemada_ha") or 0.0)

        # Demanda Agrícola y Riego (CNR / ODEPA)
        riego = self.riego_dict.get(codigo_dga, {})
        riego_demanda_lps = float(riego.get("demanda_media_agricola_lps") or 0.0)
        riego_sup_ha = float(riego.get("superficie_regada_total_ha") or 0.0)
        riego_tecnif_pct = float(riego.get("porcentaje_tecnificacion") or 0.0)
        riego_estres = str(riego.get("estres_hidrico_agricola") or "BAJO")

        # Causal graph indicators
        causales = self.causal_edges_count[codigo_dga]
        amenaza_relave_apr = causales["amenaza_relave_apr"]
        descargas_humedal = causales["descarga_ptas_humedal"]
        compite_hidro_riego = causales["compite_hidro_riego"]
        alivio_desal = causales["alivio_desalacion"]
        amenaza_incendio_embalse = causales["amenaza_incendio_embalse"]
        compite_agricola_apr = causales["compite_agricola_apr"]

        # Drought decree check
        tiene_escasez = any(
            codigo_dga in str(d.get("cuenca_codigo") or "") or region.lower() in str(d.get("region") or "").lower()
            for d in self.escasez_raw
        )
        tiene_agotamiento = any(
            codigo_dga in str(a.get("cuenca_codigo") or "") or region.lower() in str(a.get("region") or "").lower()
            for a in self.agotamiento_raw
        )

        # -------------------------------------------------------------
        # CÁLCULO DE SUB-ÍNDICES (0.0 a 100.0)
        # -------------------------------------------------------------

        # 1. Disponibilidad y Reserva Natural (I_disp) - Impulsado por Clima Real (CR2MET)
        import math
        p_val = max(p_anual_mm, 10.0)
        aridez_val = max(aridez_idx, 0.2)
        base_clima = min(90.0, max(12.0, 10.0 + 22.0 * math.log10(p_val) - 10.0 * math.log10(aridez_val)))

        # Reservas criosféricas y nival: nieves y glaciares aportan amortiguación y caudal de deshielo
        bono_reserva = min(25.0, (glac_vol_km3 * 2.0) + (fraccion_nival * 0.25) + (6.0 if glac_count > 5 else 0.0))
        # Desalación mitiga la escasez en cuencas costeras
        bono_desal = min(25.0, (desal_operativa_lps / 400.0) * 8.0)
        # Penalización por sobreotorgamiento CPA
        demanda_factor = min(25.0, (cpa_consuntivo_lps / (area_km2 * 4.0 + 1.0)))
        # Demanda de riego agrícola y bonificación por tecnificación eficiente
        penalizacion_demanda_agricola = min(15.0, (riego_demanda_lps / (area_km2 * 12.0 + 1.0)) * 2.0)
        bono_tecnificacion = min(6.0, (riego_tecnif_pct / 100.0) * 5.0)

        # Penalización por Megasequía (déficit crónico CR2 2010-presente)
        penalizacion_megasequia = round(deficit_megasequia * 0.35, 1)
        penalizacion_escasez = 12.0 if tiene_escasez else 0.0
        penalizacion_agotamiento = 8.0 if tiene_agotamiento else 0.0

        i_disp = max(5.0, min(100.0, base_clima + bono_reserva + bono_desal + bono_tecnificacion - demanda_factor - penalizacion_demanda_agricola - penalizacion_megasequia - penalizacion_escasez - penalizacion_agotamiento))

        # 2. Vulnerabilidad Ecosanitaria (I_eco)
        i_eco = 80.0
        if snaspe_count > 0:
            i_eco += min(snaspe_count * 2.5, 15.0)
        if humedales_count > 0:
            i_eco += 5.0
        if descargas_humedal > 0:
            i_eco -= min(descargas_humedal * 6.0, 40.0)
        elif ptas_count > 5:
            i_eco -= min(ptas_count * 1.5, 20.0)
        if inc_sup_ha > 0:
            i_eco -= min(20.0, (inc_sup_ha / (area_km2 * 10.0 + 100.0)) * 8.0 + (3.0 if inc_eventos > 0 else 0.0))
        i_eco = max(10.0, min(100.0, i_eco))

        # 3. Amenaza Antrópica y Pasivos Mineros (I_antrop)
        i_antrop = 100.0
        penalizacion_relaves = (relaves_abandonados * 2.0) + (relaves_activos * 0.4)
        if relaves_vol_m3 > 50_000_000:
            penalizacion_relaves += 15.0
        penalizacion_sma = sma_sanciones_count * 3.5
        if amenaza_incendio_embalse > 0:
            i_antrop -= min(amenaza_incendio_embalse * 4.0, 16.0)
        i_antrop = max(5.0, min(100.0, i_antrop - penalizacion_relaves - penalizacion_sma))

        # 4. Seguridad Humana Rural APR (I_apr)
        i_apr = 85.0
        if amenaza_relave_apr > 0:
            i_apr -= min(amenaza_relave_apr * 3.5, 45.0)
        if compite_agricola_apr > 0:
            i_apr -= min(compite_agricola_apr * 3.0, 20.0)
        elif riego_estres in ["CRÍTICO", "MUY ALTO"]:
            i_apr -= 4.0
        if tiene_escasez:
            i_apr -= 15.0
        if apr_count == 0:
            i_apr = 75.0
        i_apr = max(5.0, min(100.0, i_apr))

        # 5. Gobernanza, Especulación y Alivio (I_gob)
        i_gob = 50.0
        if jv_count > 0:
            i_gob += 20.0
        elif total_ouas > 2:
            i_gob += 10.0

        if compite_hidro_riego > 0:
            i_gob -= min(compite_hidro_riego * 2.0, 20.0)

        if desal_operativa_lps > 500.0:
            i_gob += 15.0
        elif desal_operativa_lps > 0:
            i_gob += 5.0

        if patentes_deuda_utm > 50000.0:
            i_gob -= 20.0
        elif patentes_deuda_utm > 5000.0:
            i_gob -= 10.0

        i_gob = max(10.0, min(100.0, i_gob))

        # -------------------------------------------------------------
        # ÍNDICE DE SEGURIDAD HÍDRICA COMPUESTO (ISH)
        # -------------------------------------------------------------
        ish = round(
            (0.25 * i_disp) +
            (0.20 * i_eco) +
            (0.20 * i_antrop) +
            (0.20 * i_apr) +
            (0.15 * i_gob),
            1
        )

        # Semáforo Oficial
        if ish < 45.0:
            clasificacion = "CRÍTICO"
            color = "#E53E3E"  # Rojo
        elif ish < 70.0:
            clasificacion = "VULNERABLE"
            color = "#DD6B20"  # Ámbar / Naranja
        else:
            clasificacion = "SOSTENIBLE"
            color = "#38A169"  # Verde

        # Hallazgos causales ejecutivos generados dinámicamente
        hallazgos = []
        if amenaza_relave_apr > 0:
            hallazgos.append(
                f"Amenaza Minera a APR: Se detectan {amenaza_relave_apr} aristas causales directas de depósitos de relave (críticos o abandonados) a menos de 20 km de sistemas de Agua Potable Rural."
            )
        elif relaves_abandonados > 10:
            hallazgos.append(
                f"Pasivos Mineros: Se registran {relaves_abandonados} depósitos de relave abandonados con {relaves_vol_m3 / 1e6:,.1f}M m³ de pasivos mineros en la cuenca."
            )

        if desal_operativa_lps > 0:
            hallazgos.append(
                f"Alivio Tecnológico Desalador: {desal_total_plantas} desalinizadoras aportan {desal_operativa_lps:,.1f} L/s de agua marina en operación, aliviando la presión sobre acuíferos continentales."
            )

        if compite_hidro_riego > 0:
            hallazgos.append(
                f"Conflicto Energía-Riego: {compite_hidro_riego} aristas de competencia operativa entre hidroeléctricas de embalse (>20 MW) y Juntas de Vigilancia de regantes aguas abajo."
            )

        if descargas_humedal > 0:
            hallazgos.append(
                f"Presión Ecosanitaria: {descargas_humedal} descargas de plantas de tratamiento de aguas servidas (PTAS) confluyen en proximidad (<25 km) a humedales urbanos protegidos (Ley 21.202)."
            )

        if deficit_megasequia >= 25.0:
            hallazgos.append(
                f"Megasequía Crónica (CR2): Déficit estructural de precipitación del {deficit_megasequia}% (2010-presente) con balance hídrico atmosférico deficitario ({balance_atm_mm:,.1f} mm/año)."
            )
        elif aridez_idx >= 5.0:
            hallazgos.append(
                f"Hiperaridez Extrema: Índice de aridez de {aridez_idx:,.1f} con precipitación media de apenas {p_anual_mm:,.1f} mm/año frente a {pet_anual_mm:,.1f} mm de evapotranspiración potencial."
            )

        if fraccion_nival >= 20.0 or regimen_hidro == "Nival":
            hallazgos.append(
                f"Régimen Nival Estratégico: {fraccion_nival}% de la precipitación corresponde a nieve cordillerana ({regimen_hidro}), constituyendo la torre de agua natural y reserva de deshielo estival."
            )

        if patentes_deuda_utm > 10000:
            hallazgos.append(
                f"Especulación Hídrica: Deuda acumulada de {patentes_deuda_utm:,.1f} UTM (${patentes_deuda_clp / 1e9:,.1f} mil millones CLP) en patentes por no uso de derechos consuntivos (Art. 129 bis)."
            )

        if glac_count > 0:
            hallazgos.append(
                f"Reserva Criosférica Estratégica: {glac_count} glaciares protegen {glac_vol_km3:,.2f} km³ de hielo ({glac_agua_km3:,.2f} km³ eq. agua) que alimentan la cabecera."
            )

        if inc_sup_ha >= 1000.0:
            hallazgos.append(
                f"Degradación por Incendios Forestales (CONAF): {inc_sup_ha:,.0f} ha afectadas por incendios de severidad alta en cabeceras de cuenca, con riesgo de colmatación por sedimentos y aluviones post-incendio."
            )

        if amenaza_incendio_embalse > 0:
            hallazgos.append(
                f"Amenaza de Cabecera a Embalses: {amenaza_incendio_embalse} aristas causales de degradación por incendios en el perímetro tributario de embalses estratégicos."
            )

        if riego_demanda_lps > 5000.0:
            hallazgos.append(
                f"Presión por Demanda Agrícola (CNR): Demanda de riego de {riego_demanda_lps:,.1f} L/s en {riego_sup_ha:,.0f} ha ({riego_tecnif_pct:.1f}% tecnificado), con nivel de estrés {riego_estres}."
            )

        if compite_agricola_apr > 0:
            hallazgos.append(
                f"Competencia Riego vs Consumo Humano Rural: {compite_agricola_apr} aristas de competencia por fuentes hídricas entre distritos de riego y sistemas APR."
            )

        if not hallazgos:
            hallazgos.append(
                f"Cuenca con balance hídrico regular ({zona}), caudal consuntivo de {cpa_consuntivo_lps:,.1f} L/s y {total_ouas} organizaciones de regantes registradas."
            )

        # Recomendaciones de Gobernanza según Legislación Chilena
        recomendaciones = []
        if amenaza_relave_apr > 0:
            recomendaciones.append(
                "Prioridad Sanitaria (Ley 21.435 Art. 5 bis): Desplegar telemetría continua MEE en captaciones de APR y fiscalizar estabilidad química de relaves con SERNAGEOMIN."
            )
        if inc_sup_ha >= 1000.0 or amenaza_incendio_embalse > 0:
            recomendaciones.append(
                "Restauración Hidrológica de Cabeceras: Implementar bioingeniería para control de erosión y reforestación nativa con CONAF en zonas quemadas para proteger la vida útil de embalses."
            )
        if riego_sup_ha > 2000.0 and riego_tecnif_pct < 65.0:
            recomendaciones.append(
                "Tecnificación y Eficiencia de Riego (Ley N° 18.450): Focalizar recursos CNR para conversión a riego tecnificado (goteo/microaspersión) y telemetría en canales matrices."
            )
        if deficit_megasequia >= 25.0:
            recomendaciones.append(
                "Adaptación al Cambio Climático: Formalizar el Plan Estratégico de Recursos Hídricos en Cuenca (Ley N° 21.455 de Cambio Climático y Art. 293 bis del Código de Aguas)."
            )
        if fraccion_nival >= 20.0:
            recomendaciones.append(
                "Protección de Nieves y Permafrost: Fortalecer la red de monitoreo nivométrico de alta cordillera y modelación de deshielo ante el ascenso de la isoterma cero."
            )
        if compite_hidro_riego > 0:
            recomendaciones.append(
                "Protocolo de Desembalse: Establecer convenios de extracción y turnos entre el Coordinador Eléctrico Nacional (CEN) y la Junta de Vigilancia para proteger el riego estival."
            )
        if descargas_humedal > 0:
            recomendaciones.append(
                "Supervisión D.S. 90 / SMA: Monitorear parámetros DBO5 y coliformes en descargas de PTAS hacia humedales declarados por el MMA para evitar eutrofización."
            )
        if patentes_deuda_utm > 5000:
            recomendaciones.append(
                "Cobranza Coactiva y Remate TGR: Aplicar remate judicial de derechos morosos en patentes de no uso (Art. 129 bis 10) para restituir caudales a la DGA."
            )
        if jv_count == 0 and total_ouas > 0:
            recomendaciones.append(
                "Constitución de Junta de Vigilancia: Unificar las comunidades de aguas en una Junta de Vigilancia oficial con facultades sancionatorias y reparto de caudales de sequía."
            )
        if desal_operativa_lps == 0 and zona in ["Norte Grande", "Norte Chico"]:
            recomendaciones.append(
                "Evaluación de Desalación Marina: Promover plantas desaladoras multipropósito para consumo humano y minería a fin de recuperar los acuíferos sobreexplotados."
            )
        if not recomendaciones:
            recomendaciones.append(
                "Conservación y Monitoreo: Mantener planes de gestión estratégica de cuencas de la DGA y proteger el caudal ecológico mínimo."
            )

        return {
            "codigo_dga": codigo_dga,
            "nombre": nombre,
            "region": region,
            "zona_hidrografica": zona,
            "superficie_km2": area_km2,
            "indice_seguridad_hidrica": ish,
            "clasificacion": clasificacion,
            "color_semaforo": color,
            "subindices": {
                "disponibilidad_reserva": round(i_disp, 1),
                "vulnerabilidad_ecosanitaria": round(i_eco, 1),
                "amenaza_antropica": round(i_antrop, 1),
                "seguridad_humana_apr": round(i_apr, 1),
                "gobernanza_y_alivio": round(i_gob, 1)
            },
            "metricas_clave": {
                "cpa_caudal_consuntivo_lps": round(cpa_consuntivo_lps, 2),
                "cpa_derechos_total": cpa_derechos_total,
                "precipitacion_media_anual_mm": round(p_anual_mm, 1),
                "evapotranspiracion_potencial_mm": round(pet_anual_mm, 1),
                "balance_hidrico_atmosferico_mm": round(balance_atm_mm, 1),
                "indice_aridez_medio": round(aridez_idx, 2),
                "deficit_megasequia_pct": round(deficit_megasequia, 1),
                "fraccion_nival_media_pct": round(fraccion_nival, 1),
                "regimen_hidrologico": regimen_hidro,
                "estaciones_meteorologicas_total": estaciones_meteo_total,
                "glaciares_total": glac_count,
                "glaciares_volumen_km3": round(glac_vol_km3, 3),
                "glaciares_equivalente_agua_km3": round(glac_agua_km3, 3),
                "relaves_total": relaves_total,
                "relaves_abandonados": relaves_abandonados,
                "relaves_activos": relaves_activos,
                "amenazas_relave_apr_aristas": amenaza_relave_apr,
                "descargas_ptas_humedal_aristas": descargas_humedal,
                "compite_hidro_riego_aristas": compite_hidro_riego,
                "alivio_desalacion_aristas": alivio_desal,
                "amenaza_incendio_embalse_aristas": amenaza_incendio_embalse,
                "compite_agricola_apr_aristas": compite_agricola_apr,
                "incendios_eventos_historicos": inc_eventos,
                "incendios_superficie_quemada_ha": round(inc_sup_ha, 1),
                "demanda_agricola_lps": round(riego_demanda_lps, 2),
                "superficie_regada_ha": round(riego_sup_ha, 1),
                "tecnificacion_riego_pct": round(riego_tecnif_pct, 1),
                "estres_hidrico_agricola": riego_estres,
                "patentes_no_uso_utm": round(patentes_deuda_utm, 2),
                "patentes_no_uso_clp": round(patentes_deuda_clp, 2),
                "desalacion_operativa_lps": round(desal_operativa_lps, 2),
                "desalacion_total_plantas": desal_total_plantas,
                "ptas_total": ptas_count,
                "humedales_urbanos_total": humedales_count,
                "snaspe_areas_protegidas": snaspe_count,
                "hidroelectricas_potencia_mw": round(cne_hidro_mw, 2),
                "sma_sanciones_total": sma_sanciones_count,
                "sistemas_apr_total": apr_count,
                "beneficiarios_apr": apr_beneficiarios,
                "juntas_vigilancia_total": jv_count,
                "total_organizaciones_usuarios": total_ouas,
                "decreto_escasez_activo": tiene_escasez,
                "declaracion_agotamiento_activa": tiene_agotamiento
            },
            "hallazgos_criticos": hallazgos,
            "recomendaciones_gobernanza": recomendaciones
        }

    def calcular_diagnostico_nacional(self) -> List[Dict[str, Any]]:
        """
        Retorna el ranking nacional de todas las macrocuencas ordenadas de menor a mayor
        Índice de Seguridad Hídrica (las más críticas primero).
        """
        diagnosticos = []
        for codigo in self.cuencas_dict.keys():
            diag = self.calcular_diagnostico_cuenca(codigo)
            if diag:
                diagnosticos.append(diag)

        diagnosticos.sort(key=lambda x: (x["indice_seguridad_hidrica"], -x["metricas_clave"]["amenazas_relave_apr_aristas"]))
        return diagnosticos

    def obtener_resumen_nacional(self) -> Dict[str, Any]:
        """
        Calcula un balance macro-ejecutivo de la seguridad hídrica en Chile.
        """
        todos = self.calcular_diagnostico_nacional()
        total_cuencas = len(todos)
        if total_cuencas == 0:
            return {}

        criticas = [c for c in todos if c["clasificacion"] == "CRÍTICO"]
        vulnerables = [c for c in todos if c["clasificacion"] == "VULNERABLE"]
        sostenibles = [c for c in todos if c["clasificacion"] == "SOSTENIBLE"]

        promedio_ish = round(sum(c["indice_seguridad_hidrica"] for c in todos) / total_cuencas, 1)

        total_desal_lps = sum(c["metricas_clave"]["desalacion_operativa_lps"] for c in todos)
        total_relaves_abandonados = sum(c["metricas_clave"]["relaves_abandonados"] for c in todos)
        total_amenazas_apr = sum(c["metricas_clave"]["amenazas_relave_apr_aristas"] for c in todos)
        total_descargas_humedal = sum(c["metricas_clave"]["descargas_ptas_humedal_aristas"] for c in todos)
        total_compite_hidro = sum(c["metricas_clave"]["compite_hidro_riego_aristas"] for c in todos)
        total_deuda_utm = sum(c["metricas_clave"]["patentes_no_uso_utm"] for c in todos)
        total_vol_glaciares_km3 = sum(c["metricas_clave"]["glaciares_volumen_km3"] for c in todos)
        total_agua_glaciares_km3 = sum(c["metricas_clave"]["glaciares_equivalente_agua_km3"] for c in todos)

        # Agregados hidroclimáticos nacionales
        total_p = sum(c["metricas_clave"]["precipitacion_media_anual_mm"] for c in todos)
        promedio_precip = round(total_p / total_cuencas, 1)
        total_deficit_mega = sum(c["metricas_clave"]["deficit_megasequia_pct"] for c in todos)
        promedio_deficit_mega = round(total_deficit_mega / total_cuencas, 1)
        cuencas_megasequia_severa = sum(1 for c in todos if c["metricas_clave"]["deficit_megasequia_pct"] >= 25.0)

        return {
            "total_cuencas_evaluadas": total_cuencas,
            "indice_seguridad_hidrica_nacional_promedio": promedio_ish,
            "distribucion_semaforo": {
                "criticas": len(criticas),
                "vulnerables": len(vulnerables),
                "sostenibles": len(sostenibles),
                "porcentaje_criticas": round((len(criticas) / total_cuencas) * 100, 1),
                "porcentaje_vulnerables": round((len(vulnerables) / total_cuencas) * 100, 1),
                "porcentaje_sostenibles": round((len(sostenibles) / total_cuencas) * 100, 1)
            },
            "totales_estrategicos": {
                "capacidad_desalacion_operativa_lps": round(total_desal_lps, 2),
                "relaves_abandonados_nacional": total_relaves_abandonados,
                "aristas_amenaza_relave_a_apr": total_amenazas_apr,
                "aristas_descarga_ptas_a_humedal": total_descargas_humedal,
                "aristas_competencia_hidro_riego": total_compite_hidro,
                "deuda_patentes_no_uso_utm": round(total_deuda_utm, 2),
                "reserva_glaciar_hielo_km3": round(total_vol_glaciares_km3, 3),
                "reserva_glaciar_agua_equivalente_km3": round(total_agua_glaciares_km3, 3),
                "precipitacion_promedio_nacional_mm": promedio_precip,
                "deficit_megasequia_promedio_pct": promedio_deficit_mega,
                "cuencas_con_megasequia_severa": cuencas_megasequia_severa
            },
            "top_5_cuencas_mas_criticas": [
                {
                    "codigo_dga": c["codigo_dga"],
                    "nombre": c["nombre"],
                    "region": c["region"],
                    "ish": c["indice_seguridad_hidrica"],
                    "clasificacion": c["clasificacion"],
                    "amenazas_apr": c["metricas_clave"]["amenazas_relave_apr_aristas"],
                    "relaves_abandonados": c["metricas_clave"]["relaves_abandonados"]
                }
                for c in todos[:5]
            ],
            "top_5_cuencas_mas_sostenibles": [
                {
                    "codigo_dga": c["codigo_dga"],
                    "nombre": c["nombre"],
                    "region": c["region"],
                    "ish": c["indice_seguridad_hidrica"],
                    "clasificacion": c["clasificacion"]
                }
                for c in reversed(todos[-5:])
            ]
        }
