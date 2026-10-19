"""
Advanced Interactive GIS Dashboard for Chile's National Water Infrastructure.
Features:
- Multi-base layer switcher (Esri Satellite HD, OpenTopoMap, OpenStreetMap)
- The 90 official DGA hydrographic basins with drought color-coding
- Real Vector traces of Chile's major Rivers from Andes to the Pacific (L.polyline)
- Real Vector traces of Canal Matrices de Riego (dashed polylines branching from bocatomas)
- Strategic Reservoirs (Embalses) with capacity metrics
- Major Bocatomas (Intake structures) with flow capacities
- Official BNA Fluviometric Gauging Stations with telemetry status
- Region quick-filter with animated auto-zoom (flyTo)
- Collapsible interactive DDD Control Sidebar with live Prorrateo (Art. 5 bis) simulation
"""

import json
from pathlib import Path
from typing import Optional


class ChileWaterMapGenerator:
    """
    Generates an institutional-grade Leaflet.js HTML dashboard with vector river and canal traces.
    """

    def __init__(self, data_dir: Optional[str] = None):
        if not data_dir:
            data_dir = str(Path(__file__).parent.parent.parent.parent / "data")
        self.data_dir = Path(data_dir)

    def generate_html_map(self, output_path: Optional[str] = None) -> str:
        if not output_path:
            output_path = str(self.data_dir / "mapa_cuencas_chile.html")

        cuencas_file = self.data_dir / "cuencas_dga_chile.json"
        ouas_file = self.data_dir / "registro_nacional_ouas.json"
        graph_file = self.data_dir / "knowledge_graph_chile.json"

        with open(cuencas_file, "r", encoding="utf-8") as f:
            cuencas = json.load(f)

        ouas = []
        if ouas_file.exists():
            with open(ouas_file, "r", encoding="utf-8") as f:
                ouas = json.load(f)

        drought_basins = {"051", "052", "054", "043", "045", "047"}
        decretos_file = self.data_dir / "decretos_escasez_chile.json"
        if decretos_file.exists():
            with open(decretos_file, "r", encoding="utf-8") as f:
                decs = json.load(f)
                for d in decs:
                    if d.get("es_vigente"):
                        cob = str(d.get("cobertura_territorial") or "").lower()
                        for c in cuencas:
                            if c["nombre"].lower() in cob:
                                drought_basins.add(c["codigo_dga"])

        # Cargar SHACs oficiales (Sectores Hidrogeológicos de Aprovechamiento Común)
        shac_file = self.data_dir / "shac_chile.json"
        shacs_map = []
        if shac_file.exists():
            with open(shac_file, "r", encoding="utf-8") as f:
                raw_shacs = json.load(f)
                for sh in raw_shacs:
                    cent = sh.get("centroide")
                    if cent and len(cent) == 2 and cent[0] != 0:
                        shacs_map.append({
                            "nombre": sh["nombre"],
                            "acuifero": sh.get("acuifero") or "Acuífero Subterráneo",
                            "codigo_shac": sh.get("codigo_shac"),
                            "cuenca_bna": sh.get("cuenca_asociada") or "Cuenca Nacional",
                            "codigo_cuenca_bna": sh.get("codigo_cuenca_bna") or "",
                            "region": sh.get("region") or "",
                            "area_km2": sh.get("area_km2", 0),
                            "resolucion_dga": sh.get("resolucion_dga") or "Constitución Ordinaria",
                            "lat": cent[0],
                            "lon": cent[1]
                        })

        # Cargar Red Nacional de Estaciones BNA (Fluviométricas y Pozos)
        bna_file = self.data_dir / "estaciones_bna_chile.json"
        bna_map = []
        if bna_file.exists():
            with open(bna_file, "r", encoding="utf-8") as f:
                raw_bna = json.load(f)
                for st in raw_bna:
                    tipo = st.get("tipo", "")
                    # Priorizamos fluviométricas, pozos y lagos
                    if any(k in tipo for k in ["FLUVIOMETRICA", "CONTROL DE NIVEL", "LAGOS Y EMBALSES"]):
                        coords = st.get("coordenadas", [0, 0])
                        if coords[0] != 0:
                            bna_map.append({
                                "codigo": st.get("codigo_bna"),
                                "nombre": st.get("nombre"),
                                "tipo": tipo,
                                "cuenca": st.get("cuenca"),
                                "codigo_cuenca": st.get("codigo_cuenca"),
                                "lat": coords[0],
                                "lon": coords[1],
                                "altitud": st.get("altitud_msnm", 0)
                            })

        # Cargar Sistemas Sanitarios Rurales (APR / SSR)
        apr_file = self.data_dir / "sistemas_ssr_apr_chile.json"
        apr_map = []
        if apr_file.exists():
            with open(apr_file, "r", encoding="utf-8") as f:
                raw_apr = json.load(f)
                for apr in raw_apr:
                    coords = apr.get("coordenadas")
                    if coords and len(coords) == 2 and coords[0] != 0:
                        apr_map.append({
                            "nombre": apr.get("nombre"),
                            "comuna": apr.get("comuna"),
                            "region": apr.get("region"),
                            "arranques": apr.get("arranques_domiciliarios", 0),
                            "beneficiarios": apr.get("beneficiarios_estimados", 0),
                            "tipo_adm": apr.get("tipo_administracion", "Comité APR"),
                            "lat": coords[0],
                            "lon": coords[1]
                        })

        # Cargar Glaciares Estratégicos (IPG DGA 2022)
        glaciares_file = self.data_dir / "glaciares_chile.json"
        glaciares_map = []
        if glaciares_file.exists():
            with open(glaciares_file, "r", encoding="utf-8") as f:
                raw_gla = json.load(f)
                for g in raw_gla:
                    if g.get("area_km2", 0) >= 5.0 or g.get("nombre_oficial"):
                        coords = g.get("coordenadas")
                        if coords and len(coords) == 2 and coords[0] != 0:
                            glaciares_map.append({
                                "nombre": g.get("nombre"),
                                "tipo": g.get("clasificacion"),
                                "area_km2": g.get("area_km2"),
                                "volumen_km3": g.get("volumen_km3"),
                                "cuenca": g.get("cuenca_codigo"),
                                "cuenca_nom": g.get("cuenca_nombre"),
                                "region": g.get("region"),
                                "elevacion": g.get("elevacion_media_msnm"),
                                "lat": coords[0],
                                "lon": coords[1]
                            })

        # Strategic infrastructure datasets with live storage estimates
        embalses = [
            {"nombre": "Embalse La Paloma", "cuenca": "045", "rio": "Río Grande", "lat": -30.70, "lon": -71.04, "capacidad_hm3": 750.0, "volumen_actual_hm3": 285.0, "uso": "Riego Limarí (El más grande de riego en Chile)"},
            {"nombre": "Embalse Cogotí", "cuenca": "045", "rio": "Río Cogotí", "lat": -31.05, "lon": -71.02, "capacidad_hm3": 150.0, "volumen_actual_hm3": 22.5, "uso": "Riego Combarbalá"},
            {"nombre": "Embalse Recoleta", "cuenca": "045", "rio": "Río Hurtado", "lat": -30.50, "lon": -71.18, "capacidad_hm3": 100.0, "volumen_actual_hm3": 35.0, "uso": "Riego Ovalle"},
            {"nombre": "Embalse Puclaro", "cuenca": "043", "rio": "Río Elqui", "lat": -30.01, "lon": -70.83, "capacidad_hm3": 200.0, "volumen_actual_hm3": 130.0, "uso": "Riego y Agua Potable Vicuña/La Serena"},
            {"nombre": "Embalse La Laguna", "cuenca": "043", "rio": "Río Turbio", "lat": -30.20, "lon": -70.04, "capacidad_hm3": 40.0, "volumen_actual_hm3": 28.0, "uso": "Cabecera Valle de Elqui"},
            {"nombre": "Embalse Santa Juana", "cuenca": "034", "rio": "Río Huasco", "lat": -28.67, "lon": -70.64, "capacidad_hm3": 165.0, "volumen_actual_hm3": 115.0, "uso": "Riego Valle del Huasco"},
            {"nombre": "Embalse Lautaro", "cuenca": "030", "rio": "Río Copiapó", "lat": -27.88, "lon": -69.95, "capacidad_hm3": 25.0, "volumen_actual_hm3": 6.2, "uso": "Riego Valle de Copiapó"},
            {"nombre": "Embalse El Yeso", "cuenca": "057", "rio": "Río Yeso", "lat": -33.68, "lon": -70.08, "capacidad_hm3": 250.0, "volumen_actual_hm3": 215.0, "uso": "Agua Potable Gran Santiago (Aguas Andinas)"},
            {"nombre": "Embalse Rapel", "cuenca": "060", "rio": "Río Cachapoal/Tinguiririca", "lat": -34.17, "lon": -71.49, "capacidad_hm3": 695.0, "volumen_actual_hm3": 540.0, "uso": "Hidroeléctrico y Riego"},
            {"nombre": "Embalse Colbún", "cuenca": "073", "rio": "Río Maule", "lat": -35.69, "lon": -71.28, "capacidad_hm3": 1540.0, "volumen_actual_hm3": 1120.0, "uso": "Hidroeléctrico y Convenio Riego Maule"},
            {"nombre": "Laguna del Maule", "cuenca": "073", "rio": "Río Maule", "lat": -36.01, "lon": -70.50, "capacidad_hm3": 1420.0, "volumen_actual_hm3": 680.0, "uso": "Reserva Mayor de Riego del Maule"},
            {"nombre": "Lago Laja", "cuenca": "083", "rio": "Río Laja", "lat": -37.28, "lon": -71.35, "capacidad_hm3": 5580.0, "volumen_actual_hm3": 1890.0, "uso": "Reserva Mixta Riego Biobío y Generación"}
        ]

        bocatomas = [
            {"nombre": "Bocatoma Canal San Carlos", "cuenca": "057", "rio": "Río Maipo", "lat": -33.59, "lon": -70.52, "capacidad_m3s": 65.0, "operador": "Sociedad del Canal de Maipo"},
            {"nombre": "Bocatoma Canal Zañartu", "cuenca": "083", "rio": "Río Biobío", "lat": -37.10, "lon": -72.05, "capacidad_m3s": 35.0, "operador": "Asociación Canalistas Zañartu (1819)"},
            {"nombre": "Bocatoma Canal Melado", "cuenca": "073", "rio": "Río Melado", "lat": -35.79, "lon": -71.04, "capacidad_m3s": 45.0, "operador": "Asociación Canalistas Canal Melado"},
            {"nombre": "Bocatoma San Rafael", "cuenca": "054", "rio": "Río Aconcagua", "lat": -32.85, "lon": -70.61, "capacidad_m3s": 18.0, "operador": "Asociación Canalistas Los Andes"},
            {"nombre": "Bocatoma Laja Diguillín", "cuenca": "081", "rio": "Río Laja", "lat": -37.05, "lon": -71.85, "capacidad_m3s": 29.0, "operador": "Junta de Vigilancia Diguillín"}
        ]

        estaciones_bna = [
            {"codigo": "05701001-8", "nombre": "Río Maipo en El Manzano", "cuenca": "057", "lat": -33.60, "lon": -70.40, "caudal_m3s": 42.5, "ecologico_m3s": 12.0},
            {"codigo": "05410002-3", "nombre": "Río Aconcagua en Chacabuquito", "cuenca": "054", "lat": -32.85, "lon": -70.50, "caudal_m3s": 18.2, "ecologico_m3s": 8.0},
            {"codigo": "07321003-1", "nombre": "Río Maule en Armerillo", "cuenca": "073", "lat": -35.70, "lon": -71.08, "caudal_m3s": 95.0, "ecologico_m3s": 25.0},
            {"codigo": "08310001-5", "nombre": "Río Biobío en Rucalhue", "cuenca": "083", "lat": -37.75, "lon": -71.85, "caudal_m3s": 210.0, "ecologico_m3s": 40.0}
        ]

        # High-precision vector polylines of Chile's main rivers (dense geodesic waypoints & real mean flow m3/s)
        trazas_rios = [
            # Norte Grande y Chico
            {"nombre": "Río Lluta", "cuenca": "010", "caudal_medio_m3s": 2.1, "coords": [[-17.95, -69.60], [-18.10, -69.75], [-18.25, -69.95], [-18.35, -70.05], [-18.41, -70.32]], "longitud_km": 147, "origen": "Volcán Tacora (4.200 msnm)", "desembocadura": "Océano Pacífico (Arica)"},
            {"nombre": "Río Loa", "cuenca": "021", "caudal_medio_m3s": 2.4, "coords": [[-21.20, -68.45], [-21.55, -68.62], [-21.80, -68.70], [-22.18, -68.85], [-22.45, -68.92], [-22.42, -69.15], [-22.35, -69.25], [-21.95, -69.41], [-21.65, -69.53], [-21.48, -69.78], [-21.42, -70.06]], "longitud_km": 440, "origen": "Volcán Miño (4.000 msnm)", "desembocadura": "Océano Pacífico (Caleta El Loa)"},
            {"nombre": "Río Copiapó", "cuenca": "030", "caudal_medio_m3s": 2.8, "coords": [[-28.05, -69.85], [-27.95, -69.90], [-27.88, -69.95], [-27.60, -70.15], [-27.42, -70.25], [-27.37, -70.33], [-27.35, -70.60], [-27.33, -70.92]], "longitud_km": 162, "origen": "Confluencia Jorquera y Pulido", "desembocadura": "Océano Pacífico (Puerto Viejo)"},
            {"nombre": "Río Huasco", "cuenca": "034", "caudal_medio_m3s": 5.2, "coords": [[-28.85, -69.90], [-28.75, -70.30], [-28.67, -70.64], [-28.58, -70.76], [-28.52, -71.00], [-28.47, -71.22]], "longitud_km": 198, "origen": "Confluencia Carmen y Tránsito", "desembocadura": "Océano Pacífico (Huasco)"},
            {"nombre": "Río Elqui", "cuenca": "043", "caudal_medio_m3s": 14.5, "coords": [[-30.20, -70.04], [-30.12, -70.49], [-30.01, -70.83], [-29.98, -71.05], [-29.93, -71.18], [-29.90, -71.27]], "longitud_km": 75, "origen": "Confluencia Claro y Turbio", "desembocadura": "Océano Pacífico (La Serena)"},
            {"nombre": "Río Limarí", "cuenca": "045", "caudal_medio_m3s": 18.0, "coords": [[-30.90, -70.60], [-30.70, -71.04], [-30.60, -71.20], [-30.63, -71.45], [-30.73, -71.70]], "longitud_km": 189, "origen": "Confluencia Hurtado y Grande", "desembocadura": "Océano Pacífico (Caleta El Toro)"},
            {"nombre": "Río Choapa", "cuenca": "047", "caudal_medio_m3s": 11.2, "coords": [[-31.95, -70.50], [-31.85, -70.80], [-31.75, -71.05], [-31.63, -71.30], [-31.62, -71.55]], "longitud_km": 140, "origen": "Confluencia Totoral e Illapel", "desembocadura": "Océano Pacífico (Huentelauquén)"},

            # Zona Central y Metropolitana
            {"nombre": "Río Petorca", "cuenca": "051", "caudal_medio_m3s": 1.2, "coords": [[-32.18, -70.75], [-32.25, -71.00], [-32.28, -71.25], [-32.26, -71.48]], "longitud_km": 95, "origen": "Quebrada Sobrante", "desembocadura": "Océano Pacífico (La Ligua)"},
            {"nombre": "Río La Ligua", "cuenca": "052", "caudal_medio_m3s": 2.5, "coords": [[-32.35, -70.85], [-32.40, -71.10], [-32.45, -71.30], [-32.43, -71.48]], "longitud_km": 105, "origen": "Cabildo", "desembocadura": "Océano Pacífico (Pichicuy)"},
            {"nombre": "Río Aconcagua", "cuenca": "054", "caudal_medio_m3s": 33.1, "coords": [[-32.84, -70.11], [-32.83, -70.32], [-32.83, -70.52], [-32.82, -70.61], [-32.78, -70.68], [-32.75, -70.75], [-32.76, -70.98], [-32.78, -71.18], [-32.84, -71.24], [-32.88, -71.32], [-32.92, -71.53]], "longitud_km": 142, "origen": "Confluencia Juncal y Blanco", "desembocadura": "Océano Pacífico (Concón)"},
            {"nombre": "Río Colorado (Aconcagua)", "cuenca": "054", "caudal_medio_m3s": 12.0, "coords": [[-32.78, -70.18], [-32.81, -70.35], [-32.83, -70.52]], "longitud_km": 35, "origen": "Glaciares Andinos", "desembocadura": "Confluencia Río Aconcagua"},
            {"nombre": "Río Maipo", "cuenca": "057", "caudal_medio_m3s": 92.3, "coords": [[-33.74, -69.91], [-33.68, -70.08], [-33.63, -70.18], [-33.60, -70.36], [-33.59, -70.47], [-33.59, -70.52], [-33.61, -70.68], [-33.64, -70.85], [-33.67, -70.98], [-33.69, -71.18], [-33.68, -71.42], [-33.61, -71.62]], "longitud_km": 250, "origen": "Volcán Maipo / Laguna Nacimiento", "desembocadura": "Océano Pacífico (Llolleo)"},
            {"nombre": "Río Yeso (Maipo)", "cuenca": "057", "caudal_medio_m3s": 10.5, "coords": [[-33.60, -69.95], [-33.68, -70.08], [-33.62, -70.25], [-33.60, -70.36]], "longitud_km": 40, "origen": "Embalse El Yeso", "desembocadura": "Confluencia San Gabriel (Maipo)"},
            {"nombre": "Río Mapocho", "cuenca": "057", "caudal_medio_m3s": 8.5, "coords": [[-33.32, -70.28], [-33.34, -70.45], [-33.37, -70.53], [-33.40, -70.59], [-33.41, -70.61], [-33.43, -70.65], [-33.44, -70.72], [-33.48, -70.82], [-33.58, -70.92], [-33.67, -70.98]], "longitud_km": 110, "origen": "Confluencia San Francisco y Molina", "desembocadura": "Confluencia Río Maipo (El Monte)"},
            {"nombre": "Río Cachapoal", "cuenca": "060", "caudal_medio_m3s": 94.0, "coords": [[-34.25, -70.35], [-34.20, -70.60], [-34.18, -70.75], [-34.30, -70.95], [-34.39, -71.16], [-34.17, -71.49]], "longitud_km": 170, "origen": "Glaciar Cachapoal", "desembocadura": "Embalse Rapel"},
            {"nombre": "Río Claro de Rengo", "cuenca": "060", "caudal_medio_m3s": 9.8, "coords": [[-34.40, -70.70], [-34.38, -70.85], [-34.30, -70.95]], "longitud_km": 40, "origen": "Laguna de los Cristales", "desembocadura": "Confluencia Río Cachapoal"},
            {"nombre": "Río Tinguiririca", "cuenca": "060", "caudal_medio_m3s": 52.0, "coords": [[-34.80, -70.40], [-34.65, -70.85], [-34.60, -71.05], [-34.50, -71.35], [-34.25, -71.45], [-34.17, -71.49]], "longitud_km": 167, "origen": "Volcán Tinguiririca", "desembocadura": "Embalse Rapel"},

            # Zona Centro-Sur y Sur
            {"nombre": "Río Mataquito", "cuenca": "071", "caudal_medio_m3s": 153.0, "coords": [[-35.05, -70.60], [-34.98, -71.25], [-35.00, -71.60], [-35.02, -72.05], [-35.03, -72.18]], "longitud_km": 95, "origen": "Confluencia Teno y Lontué", "desembocadura": "Océano Pacífico (Iloca)"},
            {"nombre": "Río Maule", "cuenca": "073", "caudal_medio_m3s": 310.0, "coords": [[-36.01, -70.50], [-35.88, -70.72], [-35.79, -71.04], [-35.70, -71.25], [-35.65, -71.42], [-35.58, -71.72], [-35.52, -71.91], [-35.45, -72.10], [-35.38, -72.28], [-35.32, -72.41]], "longitud_km": 240, "origen": "Laguna del Maule (2.160 msnm)", "desembocadura": "Océano Pacífico (Constitución)"},
            {"nombre": "Río Melado (Maule)", "cuenca": "073", "caudal_medio_m3s": 48.0, "coords": [[-35.95, -70.90], [-35.85, -70.98], [-35.79, -71.04]], "longitud_km": 45, "origen": "Laguna Dial", "desembocadura": "Confluencia Río Maule"},
            {"nombre": "Río Itata", "cuenca": "081", "caudal_medio_m3s": 186.0, "coords": [[-36.90, -71.70], [-36.75, -72.15], [-36.60, -72.45], [-36.45, -72.85], [-36.38, -73.02]], "longitud_km": 140, "origen": "Confluencia Cholguán y Huépil", "desembocadura": "Océano Pacífico (Vegas del Itata)"},
            {"nombre": "Río Ñuble", "cuenca": "081", "caudal_medio_m3s": 110.0, "coords": [[-36.55, -71.35], [-36.58, -71.80], [-36.60, -72.10], [-36.60, -72.45]], "longitud_km": 155, "origen": "Volcán Chillán", "desembocadura": "Confluencia Río Itata"},
            {"nombre": "Río Biobío", "cuenca": "083", "caudal_medio_m3s": 899.0, "coords": [[-38.42, -71.31], [-38.15, -71.38], [-37.89, -71.42], [-37.75, -71.85], [-37.66, -72.02], [-37.58, -72.52], [-37.45, -72.68], [-37.28, -72.71], [-37.15, -72.85], [-36.98, -73.01], [-36.82, -73.05], [-36.80, -73.16]], "longitud_km": 380, "origen": "Lagunas Galletué e Icalma", "desembocadura": "Océano Pacífico (Concepción / San Pedro)"},
            {"nombre": "Río Laja", "cuenca": "083", "caudal_medio_m3s": 180.0, "coords": [[-37.28, -71.35], [-37.25, -71.65], [-37.22, -72.05], [-37.20, -72.45], [-37.25, -72.71]], "longitud_km": 140, "origen": "Lago Laja", "desembocadura": "Confluencia Río Biobío (San Rosendo)"},
            {"nombre": "Río Imperial / Cautín", "cuenca": "091", "caudal_medio_m3s": 240.0, "coords": [[-38.45, -71.55], [-38.65, -72.05], [-38.74, -72.60], [-38.75, -73.00], [-38.78, -73.40]], "longitud_km": 174, "origen": "Volcán Lonquimay", "desembocadura": "Océano Pacífico (Puerto Saavedra)"},
            {"nombre": "Río Toltén", "cuenca": "094", "caudal_medio_m3s": 572.0, "coords": [[-39.30, -71.85], [-39.28, -72.22], [-39.20, -72.65], [-39.18, -73.00], [-39.23, -73.25]], "longitud_km": 123, "origen": "Lago Villarrica", "desembocadura": "Océano Pacífico (Tolten Viejo)"},
            {"nombre": "Río Valdivia / Calle-Calle", "cuenca": "101", "caudal_medio_m3s": 680.0, "coords": [[-39.75, -71.85], [-39.80, -72.45], [-39.82, -72.85], [-39.81, -73.24], [-39.86, -73.40]], "longitud_km": 140, "origen": "Lagos Riñihue y Panguipulli", "desembocadura": "Océano Pacífico (Corral)"},
            {"nombre": "Río Bueno", "cuenca": "103", "caudal_medio_m3s": 590.0, "coords": [[-40.20, -72.35], [-40.30, -72.80], [-40.33, -73.10], [-40.25, -73.45], [-40.24, -73.72]], "longitud_km": 130, "origen": "Lago Ranco", "desembocadura": "Océano Pacífico (La Barra)"},
            {"nombre": "Río Rahue", "cuenca": "103", "caudal_medio_m3s": 105.0, "coords": [[-40.60, -72.85], [-40.58, -73.15], [-40.33, -73.10]], "longitud_km": 120, "origen": "Lago Rupanco", "desembocadura": "Confluencia Río Bueno (Osorno)"},

            # Zona Austral
            {"nombre": "Río Baker", "cuenca": "115", "caudal_medio_m3s": 1133.0, "coords": [[-46.88, -72.82], [-46.98, -72.84], [-47.12, -72.80], [-47.22, -72.81], [-47.30, -72.85], [-47.41, -72.96], [-47.50, -73.10], [-47.65, -73.32], [-47.79, -73.53]], "longitud_km": 175, "origen": "Lago Bertrand (Cuenca General Carrera)", "desembocadura": "Océano Pacífico (Caleta Tortel)"},
            {"nombre": "Río Serrano (Torres del Paine)", "cuenca": "121", "caudal_medio_m3s": 120.0, "coords": [[-51.10, -72.95], [-51.20, -73.05], [-51.25, -73.15], [-51.38, -73.25]], "longitud_km": 38, "origen": "Lago del Toro", "desembocadura": "Seno Última Esperanza"}
        ]

        # Real geographic vector polylines of Canal Matrices de Riego (branching exactly from bocatomas)
        trazas_canales = [
            {"nombre": "Canal San Carlos (Matriz Santiago)", "cuenca": "057", "coords": [[-33.595, -70.525], [-33.540, -70.535], [-33.490, -70.550], [-33.450, -70.575], [-33.418, -70.605]], "operador": "Sociedad del Canal de Maipo (1827)", "capacidad_m3s": 65.0, "longitud_km": 32.5, "origen": "Bocatoma Las Vizcachas (Río Maipo)", "destino": "Descarga en Río Mapocho (Providencia)"},
            {"nombre": "Canal Las Mercedes (Curacaví)", "cuenca": "057", "coords": [[-33.480, -70.820], [-33.450, -70.920], [-33.430, -71.050], [-33.400, -71.180], [-33.380, -71.280]], "operador": "Asociación Canalistas Las Mercedes (1854)", "capacidad_m3s": 22.0, "longitud_km": 54.0, "origen": "Río Mapocho (Pudahuel)", "destino": "Valle de Curacaví y Casablanca"},
            {"nombre": "Canal Pirque", "cuenca": "057", "coords": [[-33.598, -70.490], [-33.620, -70.540], [-33.645, -70.590], [-33.660, -70.650]], "operador": "Asociación Canalistas Pirque", "capacidad_m3s": 15.0, "longitud_km": 18.0, "origen": "Río Maipo (El Principal)", "destino": "Riego Valle de Pirque"},
            {"nombre": "Canal Los Andes (San Rafael)", "cuenca": "054", "coords": [[-32.825, -70.610], [-32.810, -70.660], [-32.780, -70.720], [-32.760, -70.780]], "operador": "Asociación Canalistas Los Andes", "capacidad_m3s": 18.0, "longitud_km": 24.0, "origen": "Bocatoma San Rafael (Río Aconcagua 1ª Secc.)", "destino": "Riego San Felipe y Rinconada"},
            {"nombre": "Canal Mauco", "cuenca": "054", "coords": [[-32.785, -71.180], [-32.820, -71.220], [-32.860, -71.280], [-32.880, -71.350]], "operador": "Asociación Canalistas Mauco", "capacidad_m3s": 12.0, "longitud_km": 31.0, "origen": "Río Aconcagua 3ª Sección", "destino": "Quintero y Puchuncaví"},
            {"nombre": "Canal San Pedro (Quillota)", "cuenca": "054", "coords": [[-32.880, -71.250], [-32.870, -71.290], [-32.860, -71.340]], "operador": "Comunidad Canal San Pedro", "capacidad_m3s": 7.5, "longitud_km": 14.0, "origen": "Río Aconcagua (La Calera)", "destino": "Valle de Quillota"},
            {"nombre": "Canal Melado (Trasvase Andino)", "cuenca": "073", "coords": [[-35.790, -71.040], [-35.750, -71.120], [-35.710, -71.220], [-35.660, -71.320]], "operador": "Asociación Canalistas Canal Melado", "capacidad_m3s": 45.0, "longitud_km": 28.0, "origen": "Río Melado (Alto Maule)", "destino": "Trasvase a Cuenca Río Ancoa / Linares"},
            {"nombre": "Canal Maule Norte", "cuenca": "073", "coords": [[-35.600, -71.400], [-35.550, -71.500], [-35.480, -71.600], [-35.420, -71.680]], "operador": "Asociación Canalistas Maule Norte", "capacidad_m3s": 30.0, "longitud_km": 42.0, "origen": "Río Maule (Colbún)", "destino": "Riego Talca y Pelarco"},
            {"nombre": "Canal Zañartu", "cuenca": "083", "coords": [[-37.100, -72.050], [-37.050, -72.150], [-37.000, -72.250], [-36.950, -72.350]], "operador": "Asociación Canalistas Zañartu (1819)", "capacidad_m3s": 35.0, "longitud_km": 46.0, "origen": "Río Biobío (Yumbel)", "destino": "Cabrero y Laja"},
            {"nombre": "Canal Biobío Sur (Negrete)", "cuenca": "083", "coords": [[-37.580, -72.520], [-37.600, -72.560], [-37.620, -72.600], [-37.650, -72.650]], "operador": "Asociación Canalistas Negrete", "capacidad_m3s": 16.0, "longitud_km": 22.0, "origen": "Río Biobío (Negrete)", "destino": "Renaico y Angol"},
            {"nombre": "Canal Laja Diguillín", "cuenca": "081", "coords": [[-37.050, -71.850], [-36.950, -71.950], [-36.850, -72.100], [-36.750, -72.200]], "operador": "Junta de Vigilancia Diguillín", "capacidad_m3s": 29.0, "longitud_km": 58.0, "origen": "Río Laja (Tucapel)", "destino": "Trasvase Cuenca Ñuble / Diguillín"},
            {"nombre": "Canal Bellavista", "cuenca": "034", "coords": [[-28.670, -70.640], [-28.620, -70.700], [-28.550, -70.750]], "operador": "Asociación Canalistas Bellavista", "capacidad_m3s": 8.0, "longitud_km": 15.0, "origen": "Embalse Santa Juana (Río Huasco)", "destino": "Vallenar"},
            {"nombre": "Canal San Carlos de Elqui", "cuenca": "043", "coords": [[-30.050, -70.700], [-30.000, -70.750], [-29.950, -70.850]], "operador": "Asociación Canalistas San Carlos de Elqui", "capacidad_m3s": 10.0, "longitud_km": 20.0, "origen": "Río Elqui (Rivadavia)", "destino": "Vicuña"},
            {"nombre": "Canal Matriz Limarí (Paloma)", "cuenca": "045", "coords": [[-30.700, -71.040], [-30.660, -71.180], [-30.630, -71.320]], "operador": "Comunidad del Sistema Paloma", "capacidad_m3s": 25.0, "longitud_km": 35.0, "origen": "Embalse La Paloma (Río Grande)", "destino": "Ovalle y Monte Patria"}
        ]

        # Cargar Canales Matrices adicionales desde el Catastro Nacional CNR / CIREN
        canales_ciren_file = self.data_dir / "canales_riego_chile.json"
        if canales_ciren_file.exists():
            with open(canales_ciren_file, "r", encoding="utf-8") as f:
                raw_can = json.load(f)
                seen_names = {c["nombre"].lower() for c in trazas_canales}
                for can in raw_can:
                    # Incluir canales matrices mayores (longitud >= 25 km) con trazado vector
                    if can.get("longitud_km", 0) >= 25.0 and len(can.get("trazado_simplificado", [])) >= 2:
                        nom = can.get("nombre", "")
                        if nom.lower() not in seen_names:
                            trazas_canales.append({
                                "nombre": nom,
                                "cuenca": can.get("cuenca_codigo") or "",
                                "coords": can.get("trazado_simplificado"),
                                "operador": can.get("organizacion_usuarios") or can.get("junta_vigilancia") or "Organización de Usuarios de Agua (CNR)",
                                "capacidad_m3s": round(max(3.0, (can.get("acciones_agua") or 10.0) * 0.15), 1),
                                "longitud_km": can.get("longitud_km"),
                                "origen": can.get("punto_origen") or can.get("fuente_hidrica") or "Bocatoma autorizada",
                                "destino": f"Zona de Riego Cuenca {can.get('cuenca_codigo')}"
                            })
                            seen_names.add(nom.lower())

        # Cargar Sanciones Ambientales Estratégicas SMA / SNIFA
        sanciones_file = self.data_dir / "sma_sanciones_agua_chile.json"
        sanciones_sma_map = []
        if sanciones_file.exists():
            with open(sanciones_file, "r", encoding="utf-8") as f:
                raw_sma = json.load(f)
                for s in raw_sma:
                    c = s.get("coordenadas")
                    multa = s.get("multa_total_uta") or 0.0
                    if c and c.get("latitud") and c.get("longitud"):
                        if multa >= 50.0 or (s.get("es_relevante_agua") and multa >= 10.0):
                            sanciones_sma_map.append({
                                "id": s.get("id"),
                                "expediente": s.get("expediente"),
                                "titular": s.get("unidad_fiscalizable_nombre"),
                                "sector": s.get("categoria_economica"),
                                "subsector": s.get("subcategoria_economica"),
                                "estado": s.get("estado"),
                                "multa_uta": multa,
                                "cuenca": s.get("cuenca_codigo"),
                                "cuenca_nom": s.get("cuenca_nombre"),
                                "etiquetas": s.get("etiquetas_hidricas") or [],
                                "link_snifa": s.get("link_snifa"),
                                "lat": c["latitud"],
                                "lon": c["longitud"]
                            })

        # Cargar Plantas Sanitarias PTAS (SISS)
        siss_file = self.data_dir / "siss_plantas_chile.json"
        siss_ptas_map = []
        if siss_file.exists():
            with open(siss_file, "r", encoding="utf-8") as f:
                raw_siss = json.load(f)
                for p in raw_siss:
                    c = p.get("coordenadas")
                    if c and c.get("latitud") and c.get("longitud"):
                        siss_ptas_map.append({
                            "id": p.get("id"),
                            "nombre": p.get("nombre"),
                            "empresa": p.get("empresa_concesionaria"),
                            "receptor": p.get("cuerpo_receptor"),
                            "tipo_receptor": p.get("tipo_receptor"),
                            "cuenca": p.get("cuenca_codigo"),
                            "cuenca_nom": p.get("cuenca_nombre"),
                            "region": p.get("region"),
                            "lat": c["latitud"],
                            "lon": c["longitud"]
                        })

        # Cargar Humedales Urbanos Protegidos Ley 21.202 (MMA)
        mma_file = self.data_dir / "mma_humedales_chile.json"
        mma_humedales_map = []
        if mma_file.exists():
            with open(mma_file, "r", encoding="utf-8") as f:
                raw_mma = json.load(f)
                for h in raw_mma:
                    c = h.get("coordenadas")
                    if c and c.get("latitud") and c.get("longitud"):
                        mma_humedales_map.append({
                            "id": h.get("id"),
                            "codigo": h.get("codigo_humedal"),
                            "nombre": h.get("nombre"),
                            "superficie_ha": h.get("superficie_ha"),
                            "resolucion": h.get("resolucion_mma"),
                            "bcn": h.get("enlace_decreto_bcn"),
                            "comuna": h.get("comuna"),
                            "region": h.get("region"),
                            "cuenca": h.get("cuenca_codigo"),
                            "cuenca_nom": h.get("cuenca_nombre"),
                            "lat": c["latitud"],
                            "lon": c["longitud"]
                        })

        # Cargar Centrales Hidroeléctricas en Operación (CNE / SEN)
        cne_file = self.data_dir / "cne_hidroelectricas_chile.json"
        cne_hidro_map = []
        if cne_file.exists():
            with open(cne_file, "r", encoding="utf-8") as f:
                raw_cne = json.load(f)
                for ch in raw_cne:
                    c = ch.get("coordenadas")
                    if c and c.get("latitud") and c.get("longitud"):
                        cne_hidro_map.append({
                            "id": ch.get("id"),
                            "nombre": ch.get("nombre"),
                            "potencia_mw": ch.get("potencia_mw"),
                            "tipo": ch.get("tipo_tecnologia"),
                            "propietario": ch.get("propietario"),
                            "cuenca": ch.get("cuenca_codigo"),
                            "cuenca_nom": ch.get("cuenca_nombre"),
                            "region": ch.get("region"),
                            "lat": c["latitud"],
                            "lon": c["longitud"]
                        })

        # Cargar Catastro de Depósitos de Relaves Mineros (SERNAGEOMIN 2025)
        relaves_file = self.data_dir / "sernageomin_relaves_chile.json"
        sernageomin_relaves_map = []
        if relaves_file.exists():
            with open(relaves_file, "r", encoding="utf-8") as f:
                raw_rel = json.load(f)
                for r in raw_rel:
                    c = r.get("coordenadas")
                    if c and c.get("latitud") and c.get("longitud"):
                        sernageomin_relaves_map.append({
                            "id": r.get("id"),
                            "codigo": r.get("codigo_deposito"),
                            "instalacion": r.get("nombre_instalacion"),
                            "faena": r.get("nombre_faena"),
                            "titular": r.get("titular_minero"),
                            "estado": r.get("estado_operativo"),
                            "riesgo": r.get("clasificacion_riesgo"),
                            "volumen_m3": r.get("volumen_actual_m3", 0),
                            "metodo": r.get("metodo_constructivo_muro"),
                            "cuenca": r.get("cuenca_codigo"),
                            "cuenca_nom": r.get("cuenca_nombre"),
                            "region": r.get("region"),
                            "lat": c["latitud"],
                            "lon": c["longitud"]
                        })

        # Cargar Áreas Silvestres Protegidas de Cabecera (CONAF / SNASPE)
        snaspe_file = self.data_dir / "conaf_snaspe_chile.json"
        conaf_snaspe_map = []
        if snaspe_file.exists():
            with open(snaspe_file, "r", encoding="utf-8") as f:
                raw_sna = json.load(f)
                for a in raw_sna:
                    c = a.get("coordenadas_centroide")
                    if c and c.get("latitud") and c.get("longitud"):
                        conaf_snaspe_map.append({
                            "id": a.get("id"),
                            "nombre": a.get("nombre"),
                            "categoria": a.get("categoria"),
                            "superficie_ha": a.get("superficie_ha", 0),
                            "superficie_km2": a.get("superficie_km2", 0),
                            "decreto": a.get("decreto_creacion"),
                            "cuenca": a.get("cuenca_codigo"),
                            "cuenca_nom": a.get("cuenca_nombre"),
                            "region": a.get("region"),
                            "lat": c["latitud"],
                            "lon": c["longitud"]
                        })

        # Cargar Catastro de Plantas Desalinizadoras de Agua de Mar (ACADES / MOP)
        desal_file = self.data_dir / "desaladoras_chile.json"
        desaladoras_map = []
        if desal_file.exists():
            with open(desal_file, "r", encoding="utf-8") as f:
                raw_desal = json.load(f)
                for d in raw_desal:
                    c = d.get("coordenadas")
                    if c and c.get("latitud") and c.get("longitud"):
                        desaladoras_map.append({
                            "id": d.get("id"),
                            "nombre": d.get("nombre"),
                            "titular": d.get("operador") or d.get("titular_operador") or "Operador no informado",
                            "capacidad_lps": d.get("capacidad_lps", 0),
                            "capacidad_m3_dia": d.get("capacidad_m3_dia", 0),
                            "sector": d.get("sector_destino"),
                            "estado": d.get("estado_operativo") or d.get("estado_desarrollo") or "Operativo",
                            "es_operativa": d.get("es_operativa", False),
                            "cuenca": d.get("cuenca_codigo"),
                            "cuenca_nom": d.get("cuenca_nombre"),
                            "region": d.get("region"),
                            "lat": c["latitud"],
                            "lon": c["longitud"]
                        })

        # Cargar Catastro de Estaciones Meteorológicas / Clima (CR2MET / CAMELS-CL / DMC)
        clima_file = self.data_dir / "clima_estaciones_chile.json"
        clima_estaciones_map = []
        if clima_file.exists():
            with open(clima_file, "r", encoding="utf-8") as f:
                raw_clima = json.load(f)
                for c in raw_clima:
                    lat = c.get("latitud")
                    lon = c.get("longitud")
                    if lat and lon and lat != 0:
                        clima_estaciones_map.append({
                            "codigo": c.get("codigo_camels") or c.get("codigo_bna"),
                            "nombre": c.get("nombre_estacion"),
                            "cuenca": c.get("cuenca_codigo"),
                            "cuenca_nom": c.get("cuenca_nombre"),
                            "lat": lat,
                            "lon": lon,
                            "p_anual": round(float(c.get("p_anual_mm") or 0.0), 1),
                            "pet_anual": round(float(c.get("pet_anual_mm") or 0.0), 1),
                            "aridez": round(float(c.get("indice_aridez") or 0.0), 2),
                            "clase_aridez": c.get("clase_aridez", "Semiarido"),
                            "frac_nieve": round(float(c.get("fraccion_nieve") or 0.0), 3),
                            "regimen": c.get("regimen_hidrologico", "Pluvial"),
                            "deficit_megasequia": round(float(c.get("deficit_megasequia_pct") or 0.0), 1),
                            "elevacion": c.get("elevacion_msnm", 0)
                        })

        # Cargar Resumen Climático por Macrocuenca (CR2MET)
        clima_cuencas_file = self.data_dir / "clima_resumen_cuencas.json"
        clima_cuencas_map = {}
        if clima_cuencas_file.exists():
            with open(clima_cuencas_file, "r", encoding="utf-8") as f:
                raw_clima_cuencas = json.load(f)
                if isinstance(raw_clima_cuencas, list):
                    clima_cuencas_map = {c.get("cuenca_codigo"): c for c in raw_clima_cuencas if c.get("cuenca_codigo")}
                elif isinstance(raw_clima_cuencas, dict):
                    clima_cuencas_map = raw_clima_cuencas

        # Cargar Incendios Forestales Históricos Catastróficos (CONAF / KITRAL)
        incendios_file = self.data_dir / "conaf_incendios_chile.json"
        incendios_map = []
        if incendios_file.exists():
            with open(incendios_file, "r", encoding="utf-8") as f:
                raw_inc = json.load(f)
                for inc in raw_inc:
                    lat = inc.get("latitud")
                    lon = inc.get("longitud")
                    if lat and lon and lat != 0:
                        incendios_map.append({
                            "id": inc.get("id"),
                            "nombre": inc.get("nombre"),
                            "temporada": inc.get("temporada"),
                            "fecha": inc.get("fecha_inicio"),
                            "comuna": inc.get("comuna"),
                            "region": inc.get("region"),
                            "cuenca": inc.get("cuenca_codigo"),
                            "cuenca_nom": inc.get("cuenca_nombre"),
                            "superficie_ha": inc.get("superficie_ha", 0),
                            "severidad": inc.get("severidad", "ALTA"),
                            "impacto_embalse": inc.get("impacto_embalse", ""),
                            "riesgo_aluvial": inc.get("riesgo_aluvial_post_incendio", "MEDIO"),
                            "amenaza_apr": inc.get("amenaza_apr_cercanos", []),
                            "lat": lat,
                            "lon": lon
                        })

        # Cargar Distritos y Valles de Riego Destacados (CNR / ODEPA)
        riego_file = self.data_dir / "cnr_riego_predios_destacados.json"
        riego_predios_map = []
        if riego_file.exists():
            with open(riego_file, "r", encoding="utf-8") as f:
                raw_riego = json.load(f)
                for r in raw_riego:
                    lat = r.get("latitud")
                    lon = r.get("longitud")
                    if lat and lon and lat != 0:
                        riego_predios_map.append({
                            "id": r.get("id"),
                            "nombre_valle": r.get("nombre_valle"),
                            "comuna": r.get("comuna"),
                            "region": r.get("region"),
                            "cuenca": r.get("cuenca_codigo"),
                            "cuenca_nom": r.get("cuenca_nombre"),
                            "superficie_ha": r.get("superficie_ha", 0),
                            "sistema_riego": r.get("sistema_riego", "Gravitacional"),
                            "tecnificacion_pct": r.get("porcentaje_tecnificacion", 50.0),
                            "canal_fuente": r.get("canal_matriz_fuente", "Canal local"),
                            "cultivos": r.get("cultivos_principales", []),
                            "demanda_lps": r.get("demanda_estimada_lps", 0),
                            "lat": lat,
                            "lon": lon
                        })

        basins_js = json.dumps(cuencas, ensure_ascii=False)
        ouas_js = json.dumps(ouas, ensure_ascii=False)
        drought_js = json.dumps(list(drought_basins), ensure_ascii=False)
        embalses_js = json.dumps(embalses, ensure_ascii=False)
        bocatomas_js = json.dumps(bocatomas, ensure_ascii=False)
        estaciones_js = json.dumps(bna_map if bna_map else estaciones_bna, ensure_ascii=False)
        shacs_js = json.dumps(shacs_map, ensure_ascii=False)
        apr_js = json.dumps(apr_map, ensure_ascii=False)
        glaciares_js = json.dumps(glaciares_map, ensure_ascii=False)
        rios_js = json.dumps(trazas_rios, ensure_ascii=False)
        canales_js = json.dumps(trazas_canales, ensure_ascii=False)
        sanciones_js = json.dumps(sanciones_sma_map, ensure_ascii=False)
        siss_js = json.dumps(siss_ptas_map, ensure_ascii=False)
        mma_js = json.dumps(mma_humedales_map, ensure_ascii=False)
        cne_js = json.dumps(cne_hidro_map, ensure_ascii=False)
        relaves_js = json.dumps(sernageomin_relaves_map, ensure_ascii=False)
        snaspe_js = json.dumps(conaf_snaspe_map, ensure_ascii=False)
        desaladoras_js = json.dumps(desaladoras_map, ensure_ascii=False)
        clima_js = json.dumps(clima_estaciones_map, ensure_ascii=False)
        clima_cuencas_js = json.dumps(clima_cuencas_map, ensure_ascii=False)
        incendios_js = json.dumps(incendios_map, ensure_ascii=False)
        riego_js = json.dumps(riego_predios_map, ensure_ascii=False)

        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Plataforma Cartográfica Nacional de Aguas de Chile - Gemelo Digital DDD</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />

    <style>
        :root {{
            --primary: #1e3a8a;
            --primary-dark: #0f172a;
            --accent: #0284c7;
            --drought: #ef4444;
            --success: #10b981;
        }}
        body, html {{ margin: 0; padding: 0; height: 100%; font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; overflow: hidden; }}
        #app {{ display: flex; height: 100vh; width: 100vw; position: relative; }}
        #map {{ flex: 1; height: 100%; }}
        
        /* Glassmorphism Top Bar */
        .top-nav {{
            position: absolute;
            top: 16px;
            left: 60px;
            z-index: 1000;
            background: rgba(15, 23, 42, 0.88);
            backdrop-filter: blur(10px);
            color: #fff;
            padding: 10px 18px;
            border-radius: 12px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.3);
            display: flex;
            align-items: center;
            gap: 16px;
            border: 1px solid rgba(255,255,255,0.12);
        }}
        .top-nav h1 {{ margin: 0; font-size: 15px; font-weight: 700; display: flex; align-items: center; gap: 8px; }}
        .nav-select {{
            background: rgba(30, 41, 59, 0.9);
            color: #fff;
            border: 1px solid #475569;
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 13px;
            cursor: pointer;
            outline: none;
        }}

        /* Collapsible Sidebar Toggle Button */
        .sidebar-toggle-btn {{
            position: absolute;
            top: 18px;
            right: 400px;
            z-index: 1002;
            background: rgba(15, 23, 42, 0.92);
            color: #ffffff;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            transition: right 0.3s ease, background 0.2s;
        }}
        .sidebar-toggle-btn:hover {{ background: #0284c7; }}
        .sidebar-toggle-btn.collapsed {{ right: 18px; }}

        /* Clean Embed Mode (inside Angular shell) */
        body.embed-mode .sidebar,
        body.embed-mode .sidebar-toggle-btn,
        body.embed-mode .legend-card,
        body.embed-mode .top-nav {{
            display: none !important;
        }}
        body.embed-mode #map {{
            width: 100vw !important;
            height: 100vh !important;
            position: absolute !important;
            top: 0 !important;
            left: 0 !important;
            right: 0 !important;
            bottom: 0 !important;
            border-radius: 0 !important;
        }}

        /* Interactive Sidebar */
        .sidebar {{
            width: 390px;
            height: 100%;
            background: #ffffff;
            box-shadow: -4px 0 25px rgba(0,0,0,0.15);
            z-index: 1001;
            display: flex;
            flex-direction: column;
            transition: margin-right 0.3s ease;
            overflow-y: auto;
        }}
        .sidebar.collapsed {{
            margin-right: -390px;
        }}
        .sidebar-header {{
            background: var(--primary-dark);
            color: #fff;
            padding: 18px 20px;
            position: relative;
        }}
        .sidebar-header h2 {{ margin: 0 0 4px; font-size: 18px; }}
        .sidebar-header p {{ margin: 0; font-size: 12px; color: #94a3b8; }}
        .sidebar-body {{ padding: 20px; flex: 1; }}
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            margin-bottom: 12px;
        }}
        .badge-drought {{ background: #fee2e2; color: #b91c1c; border: 1px solid #f87171; }}
        .badge-normal {{ background: #e0f2fe; color: #0369a1; border: 1px solid #7dd3fc; }}
        .metric-card {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 12px;
        }}
        .metric-title {{ font-size: 11px; color: #64748b; font-weight: 600; text-transform: uppercase; }}
        .metric-value {{ font-size: 15px; font-weight: 700; color: #0f172a; margin-top: 2px; }}
        
        /* Live Prorrateo Box */
        .prorrateo-box {{
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            border-radius: 10px;
            padding: 14px;
            margin-top: 14px;
        }}
        .prorrateo-box h4 {{ margin: 0 0 8px; font-size: 13px; color: #166534; display: flex; align-items: center; gap: 6px; }}
        .input-group {{ margin-bottom: 10px; }}
        .input-group label {{ display: block; font-size: 11px; color: #374151; font-weight: 600; margin-bottom: 4px; }}
        .input-group input {{ width: 100%; box-sizing: border-box; padding: 6px 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 13px; }}
        .btn-calc {{
            background: #15803d;
            color: #fff;
            border: none;
            width: 100%;
            padding: 9px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }}
        .btn-calc:hover {{ background: #166534; }}
        .res-alpha {{ margin-top: 10px; padding: 8px; background: #fff; border-radius: 6px; font-size: 12px; border: 1px solid #86efac; }}

        /* Live Regante / Canalista Calculator Box */
        .regante-box {{
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            border-radius: 10px;
            padding: 14px;
            margin-top: 14px;
        }}
        .regante-box h4 {{ margin: 0 0 8px; font-size: 13px; color: #1e40af; display: flex; align-items: center; gap: 6px; }}
        .res-regante {{
            margin-top: 10px;
            padding: 9px;
            background: #ffffff;
            border-radius: 6px;
            font-size: 12px;
            border: 1px solid #93c5fd;
            line-height: 1.5;
        }}

        /* Legend */
        .legend-card {{
            position: absolute;
            bottom: 24px;
            left: 24px;
            z-index: 1000;
            background: rgba(255,255,255,0.95);
            padding: 14px 18px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.18);
            font-size: 12px;
            border: 1px solid #e2e8f0;
        }}
        .legend-row {{ display: flex; align-items: center; gap: 8px; margin: 5px 0; }}
        .dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}
        .line-sample {{ width: 22px; height: 4px; display: inline-block; border-radius: 2px; }}
        .line-dashed {{ width: 22px; height: 3px; display: inline-block; border-top: 3px dashed #10b981; }}

        /* River and Canal Tooltips */
        .river-tooltip {{
            background: rgba(15, 23, 42, 0.92) !important;
            color: #38bdf8 !important;
            border: 1px solid #0284c7 !important;
            border-radius: 6px !important;
            font-size: 12px !important;
            font-weight: 600 !important;
            padding: 4px 8px !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4) !important;
        }}
        .river-tooltip::before {{ border-top-color: rgba(15, 23, 42, 0.92) !important; }}

        .canal-tooltip {{
            background: rgba(15, 23, 42, 0.92) !important;
            color: #34d399 !important;
            border: 1px solid #10b981 !important;
            border-radius: 6px !important;
            font-size: 12px !important;
            font-weight: 600 !important;
            padding: 4px 8px !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4) !important;
        }}
        /* Flow Telemetry Inspector & Controls */
        .nav-toggle {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            color: #93c5fd;
            background: rgba(30, 41, 59, 0.7);
            padding: 6px 11px;
            border-radius: 8px;
            border: 1px solid #475569;
            user-select: none;
            transition: background 0.2s;
        }}
        .nav-toggle:hover {{ background: rgba(30, 41, 59, 0.95); }}
        .nav-toggle input {{ cursor: pointer; accent-color: #0284c7; margin: 0; }}

        .flow-badge {{
            display: flex;
            align-items: center;
            gap: 7px;
            font-size: 12px;
            font-weight: 600;
            color: #38bdf8;
            background: rgba(15, 23, 42, 0.85);
            padding: 6px 14px;
            border-radius: 8px;
            border: 1px solid rgba(56, 189, 248, 0.35);
            white-space: nowrap;
            box-shadow: 0 2px 10px rgba(0,0,0,0.25);
        }}

        /* Hardware-Accelerated Flow Animation */
        @keyframes flowAnimation {{
            to {{
                stroke-dashoffset: -40px;
            }}
        }}
        .flow-animated .river-poly-main {{
            stroke-dasharray: 14, 10 !important;
            animation: flowAnimation 1.2s linear infinite !important;
        }}
        .flow-animated .canal-poly-main {{
            stroke-dasharray: 8, 8 !important;
            animation: flowAnimation 1.8s linear infinite !important;
        }}
    </style>
</head>
<body>
    <div id="app">
        <!-- Floating Nav -->
        <div class="top-nav">
            <h1><i class="fa-solid fa-water"></i> Red Hídrica Nacional (DDD)</h1>
            <select id="quickNav" class="nav-select">
                <option value="">-- 🔍 Volar a Río / Canal / Cuenca --</option>
                <option value="-33.52,-70.62,11">🌊 Santiago: Río Maipo & Canal San Carlos</option>
                <option value="-32.82,-70.70,11">🌊 Valparaíso: Río Aconcagua & Canales Los Andes/Mauco</option>
                <option value="-35.68,-71.20,10">🌊 Maule: Río Maule & Canal Melado</option>
                <option value="-37.20,-72.20,10">🌊 Biobío: Río Biobío & Canal Zañartu</option>
                <option value="-30.01,-70.83,11">🌊 Coquimbo: Río Elqui & Embalse Puclaro</option>
                <option value="-30.70,-71.04,11">🌊 Limarí: Río Limarí & Embalse La Paloma</option>
                <option value="-28.67,-70.64,11">🌊 Atacama: Río Huasco & Canal Bellavista</option>
                <option value="-27.50,-70.30,10">🌊 Atacama: Río Copiapó & Embalse Lautaro</option>
                <option value="-22.40,-68.90,9">🌊 Antofagasta: Río Loa (440 km)</option>
                <option value="-18.40,-70.30,10">🌊 Arica: Río Lluta</option>
                <option value="-34.30,-70.95,10">🌊 O'Higgins: Río Cachapoal & Tinguiririca</option>
                <option value="-38.74,-72.60,10">🌊 Araucanía: Río Imperial / Cautín</option>
                <option value="-39.81,-73.24,11">🌊 Los Ríos: Río Valdivia / Calle-Calle</option>
                <option value="-47.30,-72.85,9">🌊 Aysén: Río Baker (El más caudaloso de Chile)</option>
                <option value="-51.20,-73.05,9">🌊 Magallanes: Torres del Paine & Río Serrano</option>
            </select>

            <!-- Live Flow Animation Toggle -->
            <label class="nav-toggle" title="Activar corriente hídrica animada en ríos y canales">
                <input type="checkbox" id="chkAnimFlow" onchange="toggleFlowAnimation(this.checked)">
                <span>⚡ Animación de Flujo</span>
            </label>

            <!-- Flow Telemetry Inspector Badge -->
            <div id="flowInspectorBadge" class="flow-badge">
                <i class="fa-solid fa-gauge-simple-high"></i>
                <span id="flowBadgeText">Inspección de Caudal Activa</span>
            </div>
        </div>

        <!-- Floating Toggle Button for Sidebar -->
        <button id="sidebarToggle" class="sidebar-toggle-btn" onclick="toggleSidebar()" title="Ocultar/Mostrar Panel Lateral">
            <i id="toggleIcon" class="fa-solid fa-chevron-right"></i>
        </button>

        <!-- The Map -->
        <div id="map"></div>

        <!-- Sleek DDD Sidebar -->
        <div class="sidebar" id="sidebar">
            <div class="sidebar-header">
                <h2 id="sbTitle">Cuenca del Río Maipo</h2>
                <p id="sbSubtitle">DGA 057 • Región Metropolitana</p>
            </div>
            <div class="sidebar-body">
                <div id="sbBadge" class="badge badge-normal">✅ Régimen Hídrico Normal</div>
                
                <div class="metric-card">
                    <div class="metric-title">Superficie Total</div>
                    <div class="metric-value" id="sbSuperficie">15,380 km²</div>
                </div>

                <div class="metric-card">
                    <div class="metric-title">Ríos y Tributarios Mayores</div>
                    <div style="font-size: 13px; color: #334155; margin-top: 4px;" id="sbRios">
                        Río Maipo, Río Mapocho, Río Yeso, Río Colorado, Río Volcán
                    </div>
                </div>

                <div class="metric-card">
                    <div class="metric-title">Gobernanza y Juntas de Vigilancia</div>
                    <div style="font-size: 12px; color: #1e293b; margin-top: 4px;" id="sbJVs">
                        Cargando...
                    </div>
                </div>

                <div class="metric-card" id="sbClimaCard">
                    <div class="metric-title">Balance Hidroclimático (CR2MET / DMC)</div>
                    <div style="font-size: 12px; color: #1e293b; margin-top: 4px; line-height: 1.5;" id="sbClimaInfo">
                        Cargando balance climático...
                    </div>
                </div>

                <!-- Live Prorrateo Simulator -->
                <div class="prorrateo-box">
                    <h4><i class="fa-solid fa-scale-balanced"></i> Simulador de Prorrateo (Art. 5 bis)</h4>
                    <div class="input-group">
                        <label>Caudal del Río en Estación (L/s):</label>
                        <input type="number" id="simCaudal" value="5000">
                    </div>
                    <div class="input-group">
                        <label>Demanda Vital Agua Potable/APR (L/s):</label>
                        <input type="number" id="simHumano" value="1000">
                    </div>
                    <button class="btn-calc" onclick="ejecutarSimulacionProrrateo()">Calcular Distribución Legal</button>
                    <div id="simRes" class="res-alpha" style="display: none;"></div>
                </div>

                <!-- Live Regante / Canalista Calculator -->
                <div class="regante-box">
                    <h4><i class="fa-solid fa-seedling"></i> Calculadora del Regante / Accionista</h4>
                    <div class="input-group">
                        <label>N° de Acciones de Agua (del padrón OUA):</label>
                        <input type="number" id="regAcciones" value="10" step="0.5" oninput="calcularCaudalRegante()">
                    </div>
                    <div class="input-group">
                        <label>Equivalencia Estatutaria (L/s por acción):</label>
                        <input type="number" id="regEquiv" value="1.0" step="0.1" oninput="calcularCaudalRegante()">
                    </div>
                    <div id="regResult" class="res-regante"></div>
                </div>
            </div>
        </div>

        <!-- Legend Overlay -->
        <div class="legend-card">
            <strong style="color:#0f172a; font-size:13px; display:block; margin-bottom:6px;">Leyenda Hidrográfica</strong>
            <div class="legend-row"><span class="line-sample" style="background:#0284c7;"></span> <strong>Ríos Naturales</strong> (Traza fluvial)</div>
            <div class="legend-row"><span class="line-dashed"></span> <strong>Canales Matrices</strong> (Derivación)</div>
            <div class="legend-row"><span class="dot" style="background:#ef4444;"></span> Cuenca con Decreto Sequía</div>
            <div class="legend-row"><span class="dot" style="background:#3b82f6;"></span> Cuenca Régimen Normal</div>
            <div class="legend-row"><span class="dot" style="background:#6366f1;"></span> <strong>Estación Clima / CR2MET</strong> (Red meteorológica)</div>
            <div class="legend-row"><span class="dot" style="background:#8b5cf6;"></span> <strong>Acuífero Subterráneo (SHAC)</strong></div>
            <div class="legend-row"><span class="dot" style="background:#ec4899;"></span> <strong>Agua Potable Rural (APR)</strong></div>
            <div class="legend-row"><span class="dot" style="background:#06b6d4;"></span> <strong>Glaciar / Criósfera (DGA)</strong></div>
            <div class="legend-row"><span class="dot" style="background:#dc2626;"></span> <strong>Sanción Ambiental SMA</strong> (Infracción hídrica)</div>
            <div class="legend-row"><span class="dot" style="background:#14b8a6;"></span> <strong>Planta Tratamiento PTAS (SISS)</strong></div>
            <div class="legend-row"><span class="dot" style="background:#84cc16;"></span> <strong>Humedal Urbano Ley 21.202 (MMA)</strong></div>
            <div class="legend-row"><span class="dot" style="background:#eab308;"></span> <strong>Central Hidroeléctrica (CNE)</strong></div>
            <div class="legend-row"><span class="dot" style="background:#7f1d1d;"></span> <strong>Depósito Relave Minero (SERNAGEOMIN)</strong></div>
            <div class="legend-row"><span class="dot" style="background:#15803d;"></span> <strong>Parque/Reserva Cabecera (SNASPE)</strong></div>
            <div class="legend-row"><span class="dot" style="background:#0284c7;"></span> <strong>Planta Desalinizadora (ACADES)</strong></div>
            <div class="legend-row"><span class="dot" style="background:#ea580c;"></span> <strong>Incendio Forestal (CONAF)</strong></div>
            <div class="legend-row"><span class="dot" style="background:#ca8a04;"></span> <strong>Distrito de Riego (CNR / ODEPA)</strong></div>
            <div class="legend-row"><i class="fa-solid fa-droplet" style="color:#0284c7;"></i> Embalse Estratégico</div>
            <div class="legend-row"><i class="fa-solid fa-faucet" style="color:#10b981;"></i> Bocatoma Mayor</div>
            <div class="legend-row"><i class="fa-solid fa-gauge-high" style="color:#f59e0b;"></i> Estación Fluviométrica BNA</div>
        </div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
    <script>
        // Detectar si se ejecuta embebido en iframe o con ?embed=true
        try {{
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.get('embed') === 'true' || window.self !== window.top) {{
                document.body.classList.add('embed-mode');
            }}
        }} catch (e) {{
            console.warn('Embed detection error:', e);
        }}

        // FAL-06: Sanitizador XSS para atributos y popups del mapa
        function esc(str) {{
            if (str === null || str === undefined) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }}

        const basins = {basins_js};
        const ouas = {ouas_js};
        const droughtBasins = new Set({drought_js});
        const embalses = {embalses_js};
        const bocatomas = {bocatomas_js};
        const estaciones = {estaciones_js};
        const shacs = {shacs_js};
        const aprs = {apr_js};
        const glaciares = {glaciares_js};
        const rios = {rios_js};
        const canales = {canales_js};
        const sanciones = {sanciones_js};
        const ptas = {siss_js};
        const humedales = {mma_js};
        const centrales = {cne_js};
        const relaves = {relaves_js};
        const snaspe = {snaspe_js};
        const desaladoras = {desaladoras_js};
        const clima = {clima_js};
        const climaByCuenca = {clima_cuencas_js};
        const incendios = {incendios_js};
        const distritosRiego = {riego_js};

        // FAL-06: Sanitización profunda de atributos para prevenir XSS y roturas de DOM
        function sanitizeItem(obj) {{
            if (!obj || typeof obj !== 'object') return;
            for (const key in obj) {{
                if (typeof obj[key] === 'string' && !key.startsWith('link_') && !key.startsWith('url') && !key.startsWith('coords')) {{
                    obj[key] = esc(obj[key]);
                }}
            }}
        }}

        [aprs, glaciares, sanciones, ptas, humedales, centrales, relaves, snaspe, desaladoras, clima, estaciones, shacs, embalses, bocatomas, rios, canales, incendios, distritosRiego].forEach(arr => {{
            if (Array.isArray(arr)) {{
                arr.forEach(sanitizeItem);
            }}
        }});

        // 1. Base Layer Definitions

        const osm = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 18,
            attribution: '© OpenStreetMap'
        }});

        const esriSat = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
            maxZoom: 18,
            attribution: '© Esri, Maxar, Earthstar Geographics'
        }});

        const openTopo = L.tileLayer('https://{{s}}.tile.opentopomap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 17,
            attribution: '© OpenTopoMap'
        }});

        // Map setup
        const map = L.map('map', {{
            center: [-33.5, -70.7],
            zoom: 7,
            layers: [esriSat] // Default to Satellite HD
        }});

        // Layer Controls
        const baseMaps = {{
            "🛰️ Satélite Esri HD": esriSat,
            "🗺️ Relieve Topográfico": openTopo,
            "🏙️ Calles (OpenStreetMap)": osm
        }};

        // FAL-08: MarkerCluster para capas con alta densidad de puntos
        const createClusterGroup = () => (typeof L.markerClusterGroup === 'function')
            ? L.markerClusterGroup({{ maxClusterRadius: 40, disableClusteringAtZoom: 13, chunkedLoading: true }})
            : L.layerGroup();

        // Proper layer ordering: Basins in background, lines and markers on top
        const layerCuencas = L.layerGroup().addTo(map);
        const layerRios = L.layerGroup().addTo(map);
        const layerCanales = L.layerGroup().addTo(map);
        const layerEmbalses = L.layerGroup().addTo(map);
        const layerBocatomas = L.layerGroup().addTo(map);
        const layerEstaciones = L.layerGroup().addTo(map);
        const layerShac = createClusterGroup();
        const layerApr = createClusterGroup();
        const layerGlaciares = createClusterGroup();
        const layerSma = createClusterGroup();
        const layerPtas = createClusterGroup();
        const layerHumedales = createClusterGroup();
        const layerHidro = createClusterGroup();
        const layerRelaves = createClusterGroup();
        const layerSnaspe = createClusterGroup();
        const layerDesal = createClusterGroup();
        const layerClima = createClusterGroup();
        const layerIncendios = createClusterGroup();
        const layerRiego = createClusterGroup();

        // Puente de comunicación bidireccional con el Shell de Angular
        const layerBridgeMap = {{
            'cuencas': layerCuencas,
            'aprs': layerApr,
            'relaves': layerRelaves,
            'glaciares': layerGlaciares,
            'canales': layerCanales
        }};

        window.addEventListener('message', function(e) {{
            if (!e.data || typeof e.data !== 'object') return;
            if (e.data.type === 'TOGGLE_LAYER') {{
                const lyr = layerBridgeMap[e.data.layerId];
                if (lyr) {{
                    if (e.data.visible) {{
                        if (!map.hasLayer(lyr)) map.addLayer(lyr);
                    }} else {{
                        if (map.hasLayer(lyr)) map.removeLayer(lyr);
                    }}
                }}
            }} else if (e.data.type === 'SELECT_CUENCA') {{
                const target = basins.find(function(c) {{ return c.codigo_dga === e.data.codigo; }});
                if (target) {{
                    selectBasin(target, droughtBasins.has(target.codigo_dga));
                    if (target.centroide && target.centroide[0]) {{
                        map.flyTo(target.centroide, 9, {{ duration: 1.2 }});
                    }}
                }}
            }}
        }});


        const overlays = {{
            "🌊 Ríos Naturales (Trazas)": layerRios,
            "🌾 Canales de Riego (Trazas)": layerCanales,
            "📐 Cuencas DGA (90)": layerCuencas,
            "🔥 Incendios Forestales (CONAF KITRAL)": layerIncendios,
            "🚜 Distritos de Riego (CNR / ODEPA)": layerRiego,
            "🌦️ Clima y Pluviómetros (CR2MET / DMC)": layerClima,
            "🌊 Plantas Desalinizadoras (ACADES)": layerDesal,
            "☣️ Relaves Mineros (SERNAGEOMIN)": layerRelaves,
            "🌲 Parques y Reservas (SNASPE)": layerSnaspe,
            "🏭 Plantas Sanitarias PTAS (SISS)": layerPtas,
            "🌿 Humedales Urbanos (MMA Ley 21.202)": layerHumedales,
            "⚡ Centrales Hidroeléctricas (CNE / SEN)": layerHidro,
            "⚖️ Fiscalización Ambiental SMA (SNIFA)": layerSma,
            "🧊 Glaciares y Criósfera (DGA)": layerGlaciares,
            "🚰 Agua Potable Rural (APR / SSR)": layerApr,
            "🛡️ Acuíferos Subterráneos (SHAC)": layerShac,
            "💧 Embalses Estratégicos": layerEmbalses,
            "🚪 Bocatomas Mayores": layerBocatomas,
            "📏 Red Estaciones BNA (DGA)": layerEstaciones
        }};

        L.control.layers(baseMaps, overlays, {{ position: 'topright' }}).addTo(map);

        // Group OUAs by cuenca
        const ouaByCuenca = {{}};
        ouas.forEach(o => {{
            if (!ouaByCuenca[o.cuenca_codigo]) ouaByCuenca[o.cuenca_codigo] = [];
            ouaByCuenca[o.cuenca_codigo].push(o.nombre);
        }});

        // 2. Render Basins (Polygons)
        basins.forEach(b => {{
            if (!b.bbox) return;
            const isDrought = droughtBasins.has(b.codigo_dga);
            const color = isDrought ? '#ef4444' : '#38bdf8';

            const bounds = [
                [b.bbox.lat_min, b.bbox.lon_min],
                [b.bbox.lat_max, b.bbox.lon_max]
            ];

            const rect = L.rectangle(bounds, {{
                color: color,
                weight: 1.5,
                fillColor: color,
                fillOpacity: isDrought ? 0.22 : 0.06
            }}).addTo(layerCuencas);

            rect.on('click', () => {{
                selectBasin(b, isDrought);
            }});
        }});

        // Hydraulic Scaling Functions (Logarithmic flow scaling m3/s -> px)
        function getRiverWeight(caudalMedio) {{
            if (!caudalMedio) return 4.5;
            // Scale: from 2.5px (arid rivers) to 10.5px (Baker 1133 m3/s)
            const w = 2.0 + 2.6 * Math.log10(caudalMedio + 1);
            return Math.max(2.5, Math.min(10.5, w));
        }}

        function getCanalWeight(capacidad) {{
            if (!capacidad) return 3.5;
            const w = 1.8 + 1.4 * Math.log10(capacidad + 1);
            return Math.max(2.8, Math.min(6.5, w));
        }}

        // 3. Render Pixel-Perfect River Polylines (Caudal Proporcional y Casing)
        rios.forEach(r => {{
            const riverWeight = getRiverWeight(r.caudal_medio_m3s);

            // Deep background casing for cartographic sharpness
            L.polyline(r.coords, {{
                color: '#082f49',
                weight: riverWeight + 2.8,
                opacity: 0.70,
                lineCap: 'round',
                lineJoin: 'round'
            }}).addTo(layerRios);

            const poly = L.polyline(r.coords, {{
                color: '#0284c7',
                weight: riverWeight,
                opacity: 1.0,
                lineCap: 'round',
                lineJoin: 'round',
                className: 'river-poly-main'
            }}).addTo(layerRios);

            const caudalLps = (r.caudal_medio_m3s * 1000).toLocaleString();
            poly.bindTooltip(`🌊 <strong>${{r.nombre}}</strong><br>Caudal Medio: <strong>${{r.caudal_medio_m3s}} m³/s</strong> (${{caudalLps}} L/s)<br>Grosor Hidráulico: ${{riverWeight.toFixed(1)}} px`, {{
                sticky: true,
                className: 'river-tooltip'
            }});

            poly.on('mouseover', function() {{
                this.setStyle({{ weight: riverWeight + 3.0, color: '#38bdf8' }});
                document.getElementById('flowBadgeText').innerHTML = `🌊 <strong>${{r.nombre}}</strong>: ${{r.caudal_medio_m3s}} m³/s (${{caudalLps}} L/s) • ${{r.longitud_km}} km`;
            }});
            poly.on('mouseout', function() {{
                this.setStyle({{ weight: riverWeight, color: '#0284c7' }});
                document.getElementById('flowBadgeText').innerHTML = 'Inspección de Caudal Activa';
            }});

            poly.bindPopup(`
                <div style="font-size: 13px; min-width: 250px;">
                    <strong style="color:#0284c7; font-size:16px;"><i class="fa-solid fa-water"></i> ${{r.nombre}}</strong><br>
                    <div style="margin: 6px 0; border-top: 1px solid #e2e8f0; padding-top: 6px;">
                        <strong>Cuenca DGA:</strong> Código ${{r.cuenca}}<br>
                        <strong>Caudal Medio Anual:</strong> <span style="color:#0284c7; font-weight:700;">${{r.caudal_medio_m3s}} m³/s</span> (${{caudalLps}} L/s)<br>
                        <strong>Longitud:</strong> ${{r.longitud_km}} km<br>
                        <strong>Nacimiento:</strong> ${{r.origen || 'Cordillera de los Andes'}}<br>
                        <strong>Desembocadura:</strong> ${{r.desembocadura || 'Océano Pacífico'}}<br>
                        <strong>Dirección de Flujo:</strong> Cordillera de los Andes ➔ Océano Pacífico 🌊<br>
                        <small style="color:#64748b;">Cauce natural de uso público protegido por Arts. 5 y 17 del Código de Aguas</small>
                    </div>
                </div>
            `);
        }});

        // 4. Render Real Canal Polylines (Capacidad Proporcional con Casing)
        canales.forEach(c => {{
            const canalWeight = getCanalWeight(c.capacidad_m3s);

            // Contrast casing to stand out over agricultural green terrain
            L.polyline(c.coords, {{
                color: '#0f172a',
                weight: canalWeight + 2.2,
                opacity: 0.75,
                lineCap: 'round'
            }}).addTo(layerCanales);

            const poly = L.polyline(c.coords, {{
                color: '#10b981',
                weight: canalWeight,
                opacity: 1.0,
                dashArray: '8, 8',
                lineCap: 'round',
                className: 'canal-poly-main'
            }}).addTo(layerCanales);

            const capLps = (c.capacidad_m3s * 1000).toLocaleString();
            poly.bindTooltip(`🌾 <strong>${{c.nombre}}</strong><br>Capacidad de Porte: <strong>${{c.capacidad_m3s}} m³/s</strong> (${{capLps}} L/s)`, {{
                sticky: true,
                className: 'canal-tooltip'
            }});

            poly.on('mouseover', function() {{
                this.setStyle({{ weight: canalWeight + 2.5, color: '#4ade80' }});
                document.getElementById('flowBadgeText').innerHTML = `🌾 <strong>${{c.nombre}}</strong>: ${{c.capacidad_m3s}} m³/s (${{capLps}} L/s) • Operador: ${{c.operador}}`;
            }});
            poly.on('mouseout', function() {{
                this.setStyle({{ weight: canalWeight, color: '#10b981' }});
                document.getElementById('flowBadgeText').innerHTML = 'Inspección de Caudal Activa';
            }});

            poly.bindPopup(`
                <div style="font-size: 13px; min-width: 250px;">
                    <strong style="color:#10b981; font-size:16px;"><i class="fa-solid fa-faucet"></i> ${{c.nombre}}</strong><br>
                    <div style="margin: 6px 0; border-top: 1px solid #e2e8f0; padding-top: 6px;">
                        <strong>Operador Legal:</strong> ${{c.operador}}<br>
                        <strong>Capacidad de Porte:</strong> <span style="color:#10b981; font-weight:700;">${{c.capacidad_m3s}} m³/s</span> (${{capLps}} L/s)<br>
                        <strong>Longitud Conducción:</strong> ${{c.longitud_km || 20}} km<br>
                        <strong>Origen Derivación:</strong> ${{c.origen || 'Bocatoma autorizada'}}<br>
                        <strong>Destino de Aguas:</strong> ${{c.destino || 'Zona de Riego'}}<br>
                        <small style="color:#64748b;">Obra de conducción y distribución federada</small>
                    </div>
                </div>
            `);
        }});

        // 5. Render Embalses (Reservoirs) with storage progress bar
        embalses.forEach(e => {{
            const pct = ((e.volumen_actual_hm3 / e.capacidad_hm3) * 100).toFixed(1);
            const barColor = pct < 25 ? '#ef4444' : (pct < 55 ? '#f59e0b' : '#10b981');
            const statusLabel = pct < 25 ? '🚨 Nivel Crítico' : (pct < 55 ? '⚠️ Nivel Medio' : '✅ Nivel Óptimo');

            const marker = L.circleMarker([e.lat, e.lon], {{
                radius: 8.5,
                fillColor: barColor,
                color: '#ffffff',
                weight: 2.5,
                fillOpacity: 0.95
            }}).addTo(layerEmbalses);

            marker.bindPopup(`
                <div style="font-size: 13px; min-width: 240px;">
                    <strong style="color:#0284c7; font-size:15px;"><i class="fa-solid fa-droplet"></i> ${{e.nombre}}</strong><br>
                    <strong>Río / Cuenca:</strong> ${{e.rio}} (DGA ${{e.cuenca}})<br>
                    <div style="margin: 8px 0; background:#f8fafc; padding:8px; border-radius:6px; border:1px solid #e2e8f0;">
                        <div style="display:flex; justify-content:space-between; font-size:11px; margin-bottom:4px;">
                            <span><strong>Almacenado:</strong> ${{e.volumen_actual_hm3}} hm³</span>
                            <span><strong>Capacidad:</strong> ${{e.capacidad_hm3}} hm³</span>
                        </div>
                        <div style="background:#e2e8f0; border-radius:6px; height:12px; overflow:hidden;">
                            <div style="background:${{barColor}}; width:${{pct}}%; height:100%; border-radius:6px;"></div>
                        </div>
                        <div style="text-align:right; font-size:11px; font-weight:700; color:${{barColor}}; margin-top:3px;">
                            ${{pct}}% de llenado (${{statusLabel}})
                        </div>
                    </div>
                    <small style="color:#64748b;">${{e.uso}}</small>
                </div>
            `);
        }});

        // 6. Render Bocatomas (Intakes)
        bocatomas.forEach(bc => {{
            const marker = L.circleMarker([bc.lat, bc.lon], {{
                radius: 7,
                fillColor: '#10b981',
                color: '#ffffff',
                weight: 2,
                fillOpacity: 0.95
            }}).addTo(layerBocatomas);

            marker.bindPopup(`
                <strong>🚪 ${{bc.nombre}}</strong><br>
                <strong>Río:</strong> ${{bc.rio}}<br>
                <strong>Capacidad Máxima:</strong> ${{bc.capacidad_m3s}} m³/s<br>
                <strong>Operador:</strong> ${{bc.operador}}
            `);
        }});

        // 7. Render Acuíferos Subterráneos SHAC
        shacs.forEach(sh => {{
            if (!sh.lat || sh.lat === 0) return;
            const marker = L.circleMarker([sh.lat, sh.lon], {{
                radius: 5,
                fillColor: '#8b5cf6',
                color: '#ffffff',
                weight: 1.5,
                fillOpacity: 0.85
            }}).addTo(layerShac);

            marker.bindPopup(`
                <div style="font-size: 13px; min-width: 250px;">
                    <strong style="color:#7c3aed; font-size:15px;"><i class="fa-solid fa-layer-group"></i> SHAC: ${{sh.nombre}}</strong><br>
                    <div style="margin: 6px 0; border-top: 1px solid #e2e8f0; padding-top: 6px;">
                        <strong>Acuífero:</strong> ${{sh.acuifero}}<br>
                        <strong>Código DGA:</strong> ${{sh.codigo_shac}}<br>
                        <strong>Cuenca Asociada:</strong> ${{sh.cuenca_bna}} (${{sh.codigo_cuenca_bna}})<br>
                        <strong>Región:</strong> ${{sh.region}}<br>
                        <strong>Área Acuífero:</strong> ${{sh.area_km2.toLocaleString()}} km²<br>
                        <strong>Resolución DGA:</strong> ${{sh.resolucion_dga}}<br>
                        <small style="color:#64748b;">Sector Hidrogeológico de Aprovechamiento Común (Ley 21.435)</small>
                    </div>
                </div>
            `);
        }});

        // 8. Render Red Nacional de Estaciones BNA
        estaciones.forEach(st => {{
            const isWell = st.tipo && (st.tipo.includes('NIVEL') || st.tipo.includes('POZO'));
            const isLake = st.tipo && st.tipo.includes('LAGO');
            const color = isWell ? '#a855f7' : (isLake ? '#06b6d4' : '#f59e0b');
            const icon = isWell ? 'fa-bore-hole' : 'fa-gauge-high';

            const marker = L.circleMarker([st.lat, st.lon], {{
                radius: isWell ? 5.0 : 6.5,
                fillColor: color,
                color: '#ffffff',
                weight: 1.8,
                fillOpacity: 0.95
            }}).addTo(layerEstaciones);

            marker.bindPopup(`
                <div style="font-size: 13px; min-width: 240px;">
                    <strong style="color:${{color}}; font-size:15px;"><i class="fa-solid ${{icon}}"></i> BNA ${{st.codigo}}</strong><br>
                    <div style="margin: 6px 0; border-top: 1px solid #e2e8f0; padding-top: 6px;">
                        <strong>Nombre:</strong> ${{st.nombre}}<br>
                        <strong>Tipo:</strong> ${{st.tipo || 'FLUVIOMETRICA'}}<br>
                        <strong>Cuenca:</strong> ${{st.cuenca || 'Cuenca Nacional'}}<br>
                        <strong>Altitud:</strong> ${{st.altitud || 0}} msnm<br>
                        <small style="color:#64748b;">Red Hidrométrica Nacional DGA - SNIA</small>
                    </div>
                </div>
            `);
        }});

        // 9. Render Sistemas Sanitarios Rurales (APR / SSR - Art. 5 bis)
        aprs.forEach(apr => {{
            if (!apr.lat || apr.lat === 0) return;
            const marker = L.circleMarker([apr.lat, apr.lon], {{
                radius: 4.5,
                fillColor: '#ec4899',
                color: '#ffffff',
                weight: 1.2,
                fillOpacity: 0.90
            }}).addTo(layerApr);

            marker.bindPopup(`
                <div style="font-size: 13px; min-width: 250px;">
                    <strong style="color:#db2777; font-size:15px;"><i class="fa-solid fa-hand-holding-droplet"></i> ${{apr.nombre}}</strong><br>
                    <div style="margin: 6px 0; border-top: 1px solid #e2e8f0; padding-top: 6px;">
                        <strong>Comuna:</strong> ${{apr.comuna}} (${{apr.region}})<br>
                        <strong>Administración:</strong> ${{apr.tipo_adm}}<br>
                        <strong>Arranques Domiciliarios:</strong> ${{apr.arranques.toLocaleString()}} hogares<br>
                        <strong>Población Beneficiaria:</strong> <span style="color:#db2777; font-weight:700;">${{apr.beneficiarios.toLocaleString()}} personas</span><br>
                        <small style="color:#64748b; display:block; margin-top:4px;">
                            Prioridad preferente garantizada por Art. 5 bis Ley 21.435 (Consumo Humano y Saneamiento)
                        </small>
                    </div>
                </div>
            `);
        }});

        // 10. Render Glaciares y Criósfera Estratégica (DGA - IPG 2022)
        glaciares.forEach(g => {{
            if (!g.lat || g.lat === 0) return;
            const markerRadius = g.area_km2 > 50 ? 8.5 : (g.area_km2 > 10 ? 6.5 : 4.5);
            const marker = L.circleMarker([g.lat, g.lon], {{
                radius: markerRadius,
                fillColor: '#06b6d4',
                color: '#ffffff',
                weight: 1.5,
                fillOpacity: 0.88
            }}).addTo(layerGlaciares);

            marker.bindPopup(`
                <div style="font-size: 13px; min-width: 250px;">
                    <strong style="color:#0891b2; font-size:15px;"><i class="fa-solid fa-icicles"></i> ${{g.nombre}}</strong><br>
                    <div style="margin: 6px 0; border-top: 1px solid #e2e8f0; padding-top: 6px;">
                        <strong>Tipo de Glaciar:</strong> ${{g.tipo}}<br>
                        <strong>Superficie de Hielo:</strong> <span style="color:#0891b2; font-weight:700;">${{g.area_km2.toLocaleString()}} km²</span><br>
                        <strong>Volumen Estimado:</strong> ${{g.volumen_km3 ? g.volumen_km3.toLocaleString() + ' km³' : 'Sin estimación'}}<br>
                        <strong>Cuenca Hidrográfica:</strong> DGA ${{g.cuenca}} (${{g.cuenca_nom || 'Cuenca Nacional'}})<br>
                        <strong>Región:</strong> ${{g.region}}<br>
                        <strong>Elevación Media:</strong> ${{g.elevacion ? g.elevacion + ' msnm' : 'Nival / Andina'}}<br>
                        <small style="color:#64748b; display:block; margin-top:4px;">
                            Reserva criosférica protegida. Prohibición expresa de derechos de aprovechamiento (Art. 5 bis Ley 21.435).
                        </small>
                    </div>
                </div>
            `);
        }});

        // 11. Render Sanciones Ambientales SMA (SNIFA)
        sanciones.forEach(s => {{
            if (!s.lat || s.lat === 0) return;
            const isHeavy = s.multa_uta >= 500;
            const radius = isHeavy ? 8.0 : (s.multa_uta >= 100 ? 6.0 : 4.5);
            const color = isHeavy ? '#dc2626' : (s.multa_uta >= 50 ? '#ea580c' : '#d97706');

            const marker = L.circleMarker([s.lat, s.lon], {{
                radius: radius,
                fillColor: color,
                color: '#ffffff',
                weight: 1.5,
                fillOpacity: 0.90
            }}).addTo(layerSma);

            const tagsBadge = (s.etiquetas && s.etiquetas.length > 0)
                ? s.etiquetas.map(t => `<span style="background:#fee2e2; color:#b91c1c; font-size:10px; padding:2px 6px; border-radius:4px; margin-right:4px;">${{t}}</span>`).join('')
                : '';

            marker.bindPopup(`
                <div style="font-size: 13px; min-width: 260px;">
                    <strong style="color:${{color}}; font-size:14px;"><i class="fa-solid fa-scale-balanced"></i> Expediente SMA: ${{s.expediente}}</strong><br>
                    <div style="margin: 6px 0; border-top: 1px solid #e2e8f0; padding-top: 6px;">
                        <strong>Titular / Faena:</strong> ${{s.titular}}<br>
                        <strong>Sector Económico:</strong> ${{s.sector}} (${{s.subsector}})<br>
                        <strong>Estado Proceso:</strong> <span style="font-weight:600;">${{s.estado}}</span><br>
                        <strong>Sanción Aplicada:</strong> <span style="color:#b91c1c; font-weight:700; font-size:14px;">${{s.multa_uta.toLocaleString()}} UTA</span><br>
                        <strong>Cuenca DGA:</strong> ${{s.cuenca}} (${{s.cuenca_nom || 'Cuenca Nacional'}})<br>
                        ${{tagsBadge ? '<div style="margin-top:5px;">' + tagsBadge + '</div>' : ''}}
                        <div style="margin-top:8px;">
                            <a href="${{s.link_snifa}}" target="_blank" style="color:#0284c7; text-decoration:none; font-weight:600; font-size:12px;">
                                <i class="fa-solid fa-arrow-up-right-from-square"></i> Ver Expediente Oficial SNIFA
                            </a>
                        </div>
                    </div>
                </div>
            `);
        }});

        // 12. Render Plantas de Tratamiento de Aguas Servidas (SISS - PTAS)
        ptas.forEach(p => {{
            if (!p.lat || p.lat === 0) return;
            const marker = L.circleMarker([p.lat, p.lon], {{
                radius: 5.5,
                fillColor: '#14b8a6',
                color: '#ffffff',
                weight: 1.5,
                fillOpacity: 0.90
            }}).addTo(layerPtas);

            marker.bindPopup(`
                <div style="font-size: 13px; min-width: 250px;">
                    <strong style="color:#0d9488; font-size:15px;"><i class="fa-solid fa-industry"></i> ${{p.nombre}}</strong><br>
                    <div style="margin: 6px 0; border-top: 1px solid #e2e8f0; padding-top: 6px;">
                        <strong>Empresa Sanitaria:</strong> ${{p.empresa}}<br>
                        <strong>Cuerpo Receptor:</strong> <span style="font-weight:600; color:#0f766e;">${{p.receptor}}</span><br>
                        <strong>Tipo de Descarga:</strong> ${{p.tipo_receptor}}<br>
                        <strong>Cuenca DGA:</strong> ${{p.cuenca}} (${{p.cuenca_nom || 'Cuenca Receptora'}})<br>
                        <strong>Región:</strong> ${{p.region}}<br>
                        <small style="color:#64748b; display:block; margin-top:4px;">
                            Descarga normada bajo D.S. N° 90/2000 (SISS / MMA).
                        </small>
                    </div>
                </div>
            `);
        }});

        // 13. Render Humedales Urbanos Protegidos (MMA - Ley N° 21.202)
        humedales.forEach(h => {{
            if (!h.lat || h.lat === 0) return;
            const radius = h.superficie_ha > 100 ? 7.5 : 5.0;
            const marker = L.circleMarker([h.lat, h.lon], {{
                radius: radius,
                fillColor: '#84cc16',
                color: '#ffffff',
                weight: 1.5,
                fillOpacity: 0.90
            }}).addTo(layerHumedales);

            marker.bindPopup(`
                <div style="font-size: 13px; min-width: 260px;">
                    <strong style="color:#65a30d; font-size:15px;"><i class="fa-solid fa-seedling"></i> ${{h.nombre}}</strong><br>
                    <div style="margin: 6px 0; border-top: 1px solid #e2e8f0; padding-top: 6px;">
                        <strong>Código Oficial MMA:</strong> ${{h.codigo}}<br>
                        <strong>Superficie Protegida:</strong> <span style="font-weight:700; color:#4d7c0f;">${{h.superficie_ha.toLocaleString()}} ha</span> (${{(h.superficie_ha / 100).toFixed(2)}} km²)<br>
                        <strong>Comuna / Región:</strong> ${{h.comuna}} (${{h.region}})<br>
                        <strong>Cuenca DGA:</strong> ${{h.cuenca}} (${{h.cuenca_nom || 'Cuenca Nacional'}})<br>
                        <strong>Resolución Declaratoria:</strong> ${{h.resolucion}}<br>
                        ${{h.bcn ? '<div style="margin-top:6px;"><a href="' + h.bcn + '" target="_blank" style="color:#0284c7; text-decoration:none; font-weight:600; font-size:12px;"><i class="fa-solid fa-arrow-up-right-from-square"></i> Ver Decreto Oficial BCN</a></div>' : ''}}
                    </div>
                </div>
            `);
        }});

        // 14. Render Centrales Hidroeléctricas (CNE / SEN)
        centrales.forEach(ch => {{
            if (!ch.lat || ch.lat === 0) return;
            const isGrande = ch.potencia_mw >= 100;
            const radius = isGrande ? 8.5 : (ch.potencia_mw >= 20 ? 6.5 : 4.5);
            const color = ch.tipo === 'Embalse' ? '#eab308' : '#38bdf8';

            const marker = L.circleMarker([ch.lat, ch.lon], {{
                radius: radius,
                fillColor: color,
                color: '#ffffff',
                weight: 1.5,
                fillOpacity: 0.92
            }}).addTo(layerHidro);

            marker.bindPopup(`
                <div style="font-size: 13px; min-width: 260px;">
                    <strong style="color:#b45309; font-size:15px;"><i class="fa-solid fa-bolt"></i> Central ${{ch.nombre}}</strong><br>
                    <div style="margin: 6px 0; border-top: 1px solid #e2e8f0; padding-top: 6px;">
                        <strong>Potencia Instalada:</strong> <span style="font-weight:700; color:#b45309; font-size:14px;">${{ch.potencia_mw.toLocaleString()}} MW</span><br>
                        <strong>Tecnología:</strong> <span style="font-weight:600;">Hidroeléctrica de ${{ch.tipo}}</span><br>
                        <strong>Titular / Operador:</strong> ${{ch.propietario}}<br>
                        <strong>Cuenca DGA:</strong> ${{ch.cuenca}} (${{ch.cuenca_nom || 'Cuenca Nacional'}})<br>
                        <strong>Región:</strong> ${{ch.region}}<br>
                        <small style="color:#64748b; display:block; margin-top:4px;">
                            Registrada en el SEN por la Comisión Nacional de Energía (CNE).
                        </small>
                    </div>
                </div>
            `);
        }});

        // 15. Render Depósitos de Relaves Mineros (SERNAGEOMIN 2025)
        relaves.forEach(r => {{
            if (!r.lat || r.lat === 0) return;
            const isAband = r.estado === 'ABANDONADO';
            const isCrit = r.riesgo && r.riesgo.includes('Crítico');
            const color = (isAband || isCrit) ? '#dc2626' : (r.estado === 'ACTIVO' ? '#d97706' : '#71717a');
            const radius = r.volumen_m3 > 20000000 ? 7.5 : (r.volumen_m3 > 5000000 ? 6.0 : 4.5);

            const marker = L.circleMarker([r.lat, r.lon], {{
                radius: radius,
                fillColor: color,
                color: '#ffffff',
                weight: 1.5,
                fillOpacity: 0.90
            }}).addTo(layerRelaves);

            marker.bindPopup(`
                <div style="font-size: 13px; min-width: 270px;">
                    <strong style="color:${{color}}; font-size:15px;"><i class="fa-solid fa-triangle-exclamation"></i> Relave: ${{r.instalacion}}</strong><br>
                    <div style="margin: 6px 0; border-top: 1px solid #e2e8f0; padding-top: 6px;">
                        <strong>Faena:</strong> ${{r.faena}}<br>
                        <strong>Titular / Minera:</strong> ${{r.titular}}<br>
                        <strong>Estado:</strong> <span style="font-weight:700; color:${{color}};">${{r.estado}}</span><br>
                        <strong>Clasificación Riesgo:</strong> ${{r.riesgo}}<br>
                        <strong>Método Constructivo:</strong> ${{r.metodo}}<br>
                        <strong>Volumen Actual:</strong> ${{r.volumen_m3 ? (r.volumen_m3 / 1000000).toFixed(2) + ' millones m³' : 'Sin estimación'}}<br>
                        <strong>Cuenca DGA:</strong> ${{r.cuenca}} (${{r.cuenca_nom || 'Cuenca Receptora'}})<br>
                        <strong>Comuna:</strong> ${{r.comuna}} (${{r.region}})<br>
                        <small style="color:#64748b; display:block; margin-top:4px;">
                            Catastro Oficial SERNAGEOMIN (Ley N° 20.551 de Cierre de Faenas).
                        </small>
                    </div>
                </div>
            `);
        }});

        // 16. Render Áreas Silvestres Protegidas de Cabecera (CONAF / SNASPE)
        snaspe.forEach(a => {{
            if (!a.lat || a.lat === 0) return;
            const isParque = a.categoria === 'Parque Nacional';
            const color = isParque ? '#15803d' : '#059669';
            const radius = a.superficie_ha > 100000 ? 8.5 : (a.superficie_ha > 20000 ? 6.5 : 5.0);

            const marker = L.circleMarker([a.lat, a.lon], {{
                radius: radius,
                fillColor: color,
                color: '#ffffff',
                weight: 1.5,
                fillOpacity: 0.88
            }}).addTo(layerSnaspe);

            marker.bindPopup(`
                <div style="font-size: 13px; min-width: 270px;">
                    <strong style="color:${{color}}; font-size:15px;"><i class="fa-solid fa-tree"></i> ${{a.nombre}}</strong><br>
                    <div style="margin: 6px 0; border-top: 1px solid #e2e8f0; padding-top: 6px;">
                        <strong>Categoría:</strong> <span style="font-weight:600; color:${{color}};">${{a.categoria}}</span><br>
                        <strong>Superficie Protegida:</strong> <span style="font-weight:700;">${{a.superficie_ha.toLocaleString()}} ha</span> (${{a.superficie_km2.toLocaleString()}} km²)<br>
                        <strong>Decreto de Creación:</strong> ${{a.decreto}}<br>
                        <strong>Cuenca DGA:</strong> ${{a.cuenca}} (${{a.cuenca_nom || 'Cabecera de Cuenca'}})<br>
                        <strong>Región:</strong> ${{a.region}}<br>
                        <small style="color:#64748b; display:block; margin-top:4px;">
                            Área Silvestre Protegida por el Estado (SNASPE / Ley SBAP). Reserva estratégica de cabecera.
                        </small>
                    </div>
                </div>
            `);
        }});

        // 17. Render Plantas Desalinizadoras de Agua de Mar (ACADES / MOP)
        desaladoras.forEach(d => {{
            if (!d.lat || d.lat === 0) return;
            const isOp = d.es_operativa;
            const color = isOp ? '#0284c7' : '#64748b';
            const radius = d.capacidad_lps > 2000 ? 8.5 : (d.capacidad_lps > 500 ? 7.0 : 5.0);

            const marker = L.circleMarker([d.lat, d.lon], {{
                radius: radius,
                fillColor: color,
                color: '#ffffff',
                weight: 2.0,
                fillOpacity: 0.95
            }}).addTo(layerDesal);

            marker.bindPopup(`
                <div style="font-size: 13px; min-width: 270px;">
                    <strong style="color:${{color}}; font-size:15px;"><i class="fa-solid fa-water"></i> ${{d.nombre}}</strong><br>
                    <div style="margin: 6px 0; border-top: 1px solid #e2e8f0; padding-top: 6px;">
                        <strong>Operador / Titular:</strong> ${{d.titular}}<br>
                        <strong>Estado:</strong> <span style="font-weight:700; color:${{color}};">${{d.estado}}</span><br>
                        <strong>Sector de Destino:</strong> ${{d.sector}}<br>
                        <strong>Capacidad Producción:</strong> <span style="font-weight:700; color:#0284c7;">${{d.capacidad_lps.toLocaleString()}} L/s</span> (${{d.capacidad_m3_dia.toLocaleString()}} m³/día)<br>
                        <strong>Cuenca Abastecida:</strong> ${{d.cuenca}} (${{d.cuenca_nom || 'Cuenca Costera'}})<br>
                        <strong>Región:</strong> ${{d.region}}<br>
                        <small style="color:#64748b; display:block; margin-top:4px;">
                            Fuente: Catastro Oficial ACADES / MOP de Desalación Marina.
                        </small>
                    </div>
                </div>
            `);
        }});

        // 18. Render Estaciones Meteorológicas / Clima (CR2MET / CAMELS-CL / DMC)
        clima.forEach(c => {{
            if (!c.lat || c.lat === 0) return;
            let color = '#3b82f6';
            if (c.regimen === 'Nival') color = '#6366f1';
            else if (c.regimen === 'Pluvio-Nival') color = '#06b6d4';
            else if (c.regimen === 'Glacio-Nival') color = '#a855f7';

            const radius = c.p_anual > 1500 ? 6.5 : (c.p_anual > 500 ? 5.0 : 4.0);

            const marker = L.circleMarker([c.lat, c.lon], {{
                radius: radius,
                fillColor: color,
                color: '#ffffff',
                weight: 1.5,
                fillOpacity: 0.90
            }}).addTo(layerClima);

            marker.bindPopup(`
                <div style="font-size: 13px; min-width: 270px;">
                    <strong style="color:${{color}}; font-size:15px;"><i class="fa-solid fa-cloud-sun-rain"></i> ${{c.nombre}}</strong><br>
                    <div style="margin: 6px 0; border-top: 1px solid #e2e8f0; padding-top: 6px;">
                        <strong>Código Oficial:</strong> ${{c.codigo}}<br>
                        <strong>Régimen Hidrológico:</strong> <span style="font-weight:700; color:${{color}};">${{c.regimen}}</span><br>
                        <strong>Precipitación Anual:</strong> <span style="font-weight:700; color:#0284c7;">${{c.p_anual.toFixed(1)}} mm/año</span><br>
                        <strong>Evapotranspiración Potencial:</strong> ${{c.pet_anual.toFixed(1)}} mm/año<br>
                        <strong>Índice de Aridez:</strong> ${{c.aridez.toFixed(2)}} (${{c.clase_aridez}})<br>
                        <strong>Fracción Nival:</strong> ${{((c.frac_nieve || 0) * 100).toFixed(1)}}%<br>
                        <strong>Déficit Megasequía (CR2):</strong> <span style="font-weight:700; color:${{c.deficit_megasequia > 25 ? '#dc2626' : '#d97706'}};">-${{c.deficit_megasequia.toFixed(1)}}%</span><br>
                        <strong>Elevación:</strong> ${{c.elevacion}} msnm<br>
                        <strong>Cuenca DGA:</strong> ${{c.cuenca}} (${{c.cuenca_nom || 'Cuenca Nacional'}})<br>
                        <small style="color:#64748b; display:block; margin-top:4px;">
                            Fuente: CR2MET / CAMELS-CL / Dirección Meteorológica de Chile (DMC).
                        </small>
                    </div>
                </div>
            `);
        }});

        // 19. Render Incendios Forestales (CONAF / KITRAL)
        incendios.forEach(inc => {{
            if (!inc.lat || inc.lat === 0) return;
            const color = inc.severidad === 'EXTREMA' ? '#b91c1c' : (inc.severidad === 'MUY ALTA' ? '#ea580c' : '#f97316');
            const radius = inc.superficie_ha > 30000 ? 9.0 : (inc.superficie_ha > 5000 ? 7.5 : 6.0);

            const marker = L.circleMarker([inc.lat, inc.lon], {{
                radius: radius,
                fillColor: color,
                color: '#ffffff',
                weight: 2.0,
                fillOpacity: 0.90
            }}).addTo(layerIncendios);

            marker.bindPopup(`
                <div style="font-size: 13px; min-width: 280px;">
                    <strong style="color:${{color}}; font-size:15px;"><i class="fa-solid fa-fire"></i> ${{inc.nombre}}</strong><br>
                    <div style="margin: 6px 0; border-top: 1px solid #e2e8f0; padding-top: 6px;">
                        <strong>Temporada:</strong> ${{inc.temporada}} (Inicio: ${{inc.fecha}})<br>
                        <strong>Severidad:</strong> <span style="font-weight:700; color:${{color}};">${{inc.severidad}}</span><br>
                        <strong>Superficie Quemada:</strong> <span style="font-weight:700; color:#dc2626;">${{inc.superficie_ha.toLocaleString()}} ha</span><br>
                        <strong>Comuna / Región:</strong> ${{inc.comuna}}, ${{inc.region}}<br>
                        <strong>Cuenca DGA:</strong> ${{inc.cuenca}} (${{inc.cuenca_nom || 'Cuenca Hidrográfica'}})<br>
                        <strong>Impacto en Embalses:</strong> ${{inc.impacto_embalse || 'Sedimentación de cuenca'}}<br>
                        <strong>Riesgo Aluvial Post-Incendio:</strong> <span style="font-weight:700; color:${{inc.riesgo_aluvial === 'CRÍTICO' ? '#b91c1c' : '#ea580c'}};">${{inc.riesgo_aluvial}}</span><br>
                        <small style="color:#64748b; display:block; margin-top:4px;">
                            Fuente: CONAF / Sistema KITRAL - Gestión de Incendios y Cuencas.
                        </small>
                    </div>
                </div>
            `);
        }});

        // 20. Render Distritos y Valles de Riego (CNR / ODEPA)
        distritosRiego.forEach(r => {{
            if (!r.lat || r.lat === 0) return;
            const isTecnif = r.tecnificacion_pct >= 60.0;
            const color = isTecnif ? '#16a34a' : '#ca8a04';
            const radius = r.superficie_ha > 15000 ? 8.5 : (r.superficie_ha > 5000 ? 7.0 : 5.5);

            const marker = L.circleMarker([r.lat, r.lon], {{
                radius: radius,
                fillColor: color,
                color: '#ffffff',
                weight: 2.0,
                fillOpacity: 0.90
            }}).addTo(layerRiego);

            marker.bindPopup(`
                <div style="font-size: 13px; min-width: 280px;">
                    <strong style="color:${{color}}; font-size:15px;"><i class="fa-solid fa-wheat-awn"></i> ${{r.nombre_valle}}</strong><br>
                    <div style="margin: 6px 0; border-top: 1px solid #e2e8f0; padding-top: 6px;">
                        <strong>Sistema Predominante:</strong> <span style="font-weight:600; color:${{color}};">${{r.sistema_riego}}</span><br>
                        <strong>Tecnificación:</strong> <span style="font-weight:700; color:${{isTecnif ? '#16a34a' : '#ca8a04'}};">${{r.tecnificacion_pct}}%</span><br>
                        <strong>Superficie Regada:</strong> ${{r.superficie_ha.toLocaleString()}} ha<br>
                        <strong>Canal Matriz Fuente:</strong> ${{r.canal_fuente}}<br>
                        <strong>Demanda Estimada:</strong> <span style="font-weight:700; color:#0284c7;">${{r.demanda_lps.toLocaleString()}} L/s</span><br>
                        <strong>Cultivos Principales:</strong> ${{(r.cultivos || []).join(', ')}}<br>
                        <strong>Cuenca DGA:</strong> ${{r.cuenca}} (${{r.cuenca_nom || 'Valle Regado'}})<br>
                        <small style="color:#64748b; display:block; margin-top:4px;">
                            Fuente: Comisión Nacional de Riego (CNR) / ODEPA - Censo Agropecuario.
                        </small>
                    </div>
                </div>
            `);
        }});

        // Function: Select Basin and fill DDD Sidebar
        function selectBasin(b, isDrought) {{
            // Notificar a Angular Shell vía postMessage
            if (window.parent && window.parent !== window) {{
                try {{
                    window.parent.postMessage({{
                        type: 'CUENCA_SELECTED',
                        cuencaCodigo: b.codigo_dga,
                        cuencaNombre: b.nombre,
                        region: b.region,
                        isDrought: !!isDrought
                    }}, '*');
                }} catch (err) {{
                    console.warn('postMessage to parent failed:', err);
                }}
            }}

            const elTitle = document.getElementById('sbTitle');
            if (elTitle) elTitle.innerText = b.nombre;
            const elSub = document.getElementById('sbSubtitle');
            if (elSub) elSub.innerText = `Código DGA ${{b.codigo_dga}} • Región ${{b.region}}`;
            
            const badge = document.getElementById('sbBadge');
            if (badge) {{
                if (isDrought) {{
                    badge.className = 'badge badge-drought';
                    badge.innerHTML = '⚠️ DECRETO DE ESCASEZ DGA ACTIVO (Art. 314)';
                }} else {{
                    badge.className = 'badge badge-normal';
                    badge.innerHTML = '✅ Régimen Hídrico Normal';
                }}
            }}

            const elSup = document.getElementById('sbSuperficie');
            if (elSup) elSup.innerText = `${{b.superficie_km2.toLocaleString()}} km²`;
            const elRios = document.getElementById('sbRios');
            if (elRios) elRios.innerText = (b.rios_principales || []).join(', ') || 'Río principal';

            // Balance Climático
            const clim = climaByCuenca[b.codigo_dga];
            if (clim) {{
                const megasequiaStr = clim.deficit_megasequia_pct > 0 
                    ? `<span style=\"color:#dc2626; font-weight:700;\">-${{clim.deficit_megasequia_pct.toFixed(1)}}%</span>` 
                    : '<span style=\"color:#10b981;\">0%</span>';
                document.getElementById('sbClimaInfo').innerHTML = 
                    `🌧️ <strong>P:</strong> ${{(clim.precipitacion_media_anual_mm || 0).toFixed(0)}} mm/año | <strong>PET:</strong> ${{(clim.evapotranspiracion_potencial_mm || 0).toFixed(0)}} mm/año<br>` +
                    `🏜️ <strong>Aridez:</strong> ${{(clim.indice_aridez_medio || 0).toFixed(2)}} (${{clim.clasificacion_estres_climatico || 'Semiarido'}})<br>` +
                    `❄️ <strong>Régimen:</strong> ${{clim.regimen_hidrologico_predominante || 'Pluvial'}} | <strong>Megasequía:</strong> ${{megasequiaStr}}`;
            }} else {{
                document.getElementById('sbClimaInfo').innerHTML = '<em>Sin estación meteorológica de referencia</em>';
            }}

            const jvs = ouaByCuenca[b.codigo_dga] || [];
            if (jvs.length > 0) {{
                document.getElementById('sbJVs').innerHTML = '<ul style=\"padding-left:16px; margin:0;\">' + 
                    jvs.map(j => `<li>${{j}}</li>`).join('') + '</ul>';
            }} else {{
                document.getElementById('sbJVs').innerHTML = '<em>Sin juntas registradas en esta cuenca</em>';
            }}
        }}

        // Quick FlyTo Navigation
        document.getElementById('quickNav').addEventListener('change', function(e) {{
            if (!this.value) return;
            const parts = this.value.split(',');
            map.flyTo([parseFloat(parts[0]), parseFloat(parts[1])], parseInt(parts[2]), {{
                duration: 1.5
            }});
        }});

        // Sidebar Collapsible Toggle Function
        function toggleSidebar() {{
            const sb = document.getElementById('sidebar');
            const btn = document.getElementById('sidebarToggle');
            const icon = document.getElementById('toggleIcon');
            sb.classList.toggle('collapsed');
            btn.classList.toggle('collapsed');
            if (sb.classList.contains('collapsed')) {{
                icon.className = 'fa-solid fa-chevron-left';
                btn.title = 'Mostrar Panel Lateral';
            }} else {{
                icon.className = 'fa-solid fa-chevron-right';
                btn.title = 'Ocultar Panel Lateral';
            }}
            setTimeout(() => {{
                map.invalidateSize();
            }}, 320);
        }}

        // Toggle Hardware-Accelerated Flow Animation
        function toggleFlowAnimation(enabled) {{
            document.getElementById('map').classList.toggle('flow-animated', enabled);
            if (enabled) {{
                document.getElementById('flowBadgeText').innerHTML = '⚡ Corriente fluvial y derivaciones en movimiento activo';
            }} else {{
                document.getElementById('flowBadgeText').innerHTML = 'Inspección de Caudal Activa';
            }}
        }}

        // Global State for Prorrateo Factor
        let currentAlpha = 0.70;

        // Live Regante / Canalista Calculator
        function calcularCaudalRegante() {{
            const acciones = parseFloat(document.getElementById('regAcciones').value) || 0;
            const equiv = parseFloat(document.getElementById('regEquiv').value) || 0;
            const nominalLps = acciones * equiv;
            const efectivoLps = nominalLps * currentAlpha;
            const m3Dia = (efectivoLps * 86400) / 1000;

            let color = currentAlpha >= 1.0 ? '#15803d' : (currentAlpha >= 0.7 ? '#ca8a04' : '#dc2626');

            const resBox = document.getElementById('regResult');
            resBox.innerHTML = `
                <strong>Entrega en Bocatoma / Marco Partidor:</strong><br>
                • Dotación Nominal Estatutaria: <strong>${{nominalLps.toFixed(2)}} L/s</strong><br>
                • Factor Prorrateo Vigente (&alpha;): <strong style=\"color:${{color}};\">${{(currentAlpha * 100).toFixed(0)}}%</strong><br>
                • Caudal Efectivo a Recibir: <strong style=\"color:${{color}}; font-size:14px;\">${{efectivoLps.toFixed(2)}} L/s</strong><br>
                • Volumen Diario Estimado: <strong>${{m3Dia.toLocaleString(undefined, {{maximumFractionDigits: 1}})}} m³/día</strong>
            `;
        }}

        // Live Simulation in Sidebar (Art. 5 bis)
        function ejecutarSimulacionProrrateo() {{
            const caudal = parseFloat(document.getElementById('simCaudal').value);
            const humano = parseFloat(document.getElementById('simHumano').value);
            const ecologico = 500.0;
            const permanenteDemand = 5000.0;

            const resDiv = document.getElementById('simRes');
            resDiv.style.display = 'block';

            if (caudal < humano) {{
                currentAlpha = 0.0;
                calcularCaudalRegante();
                resDiv.style.background = '#fee2e2';
                resDiv.style.borderColor = '#f87171';
                resDiv.innerHTML = '<strong>🚨 EMERGENCIA SANITARIA:</strong> El caudal no alcanza para el agua potable.';
                return;
            }}

            const remanente = caudal - humano - ecologico;
            let alpha = remanente / permanenteDemand;
            if (alpha > 1.0) alpha = 1.0;
            if (alpha < 0.0) alpha = 0.0;

            currentAlpha = alpha;
            calcularCaudalRegante();

            const pct = (alpha * 100).toFixed(1);
            let color = alpha >= 1.0 ? '#166534' : (alpha >= 0.7 ? '#ca8a04' : '#dc2626');

            resDiv.style.background = '#f0fdf4';
            resDiv.style.borderColor = '#86efac';
            resDiv.innerHTML = `
                <strong>Veredicto Art. 5 bis:</strong><br>
                • Agua Potable: <strong>100% Satisfecha</strong> (${{humano}} L/s)<br>
                • Caudal Ecológico: <strong>Reservado</strong> (${{ecologico}} L/s)<br>
                • Factor Agricultores: <strong style=\"color:${{color}};\">${{pct}}% de su dotación</strong> (&alpha; = ${{alpha.toFixed(2)}})<br>
                • Derechos Eventuales: <strong>${{alpha >= 1.0 ? 'Autorizados' : 'BLOQUEADOS (0 L/s)'}}</strong>
            `;
        }}

        // Initialize default view with Maipo and Regante calculator
        const defaultMaipo = basins.find(b => b.codigo_dga === '057');
        if (defaultMaipo) selectBasin(defaultMaipo, false);
        calcularCaudalRegante();
    </script>
</body>
</html>"""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return output_path
