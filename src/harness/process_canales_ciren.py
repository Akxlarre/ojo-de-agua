"""
Pipeline de procesamiento del Catastro Nacional de Canales de Riego e Infraestructura Hídrica
(Comisión Nacional de Riego CNR / CIREN / IDE Minagri).
Extrae los 12.233 canales de riego georreferenciados, proyecta las coordenadas UTM 19S a WGS84,
y estructura las relaciones jerárquicas con las Juntas de Vigilancia y Cuencas DGA.
"""

import json
import math
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import shapefile

BASE_DIR = Path(__file__).parent.parent.parent
RAW_SHP = BASE_DIR / "data" / "dga_raw" / "canales_nacional_final" / "canales_nacional_final.shp"
DATA_DIR = BASE_DIR / "data"


def utm_19s_to_latlon(easting: float, northing: float) -> Tuple[float, float]:
    """Convierte coordenadas UTM Zona 19S (WGS84) a grados geográficos Latitud/Longitud."""
    a = 6378137.0
    f = 1 / 298.257223563
    b = a * (1 - f)
    e = math.sqrt(1 - (b / a) ** 2)
    e_prime_sq = (e * a / b) ** 2
    k0 = 0.9996
    cm = -69.0  # Meridiano Central UTM Zona 19S

    x = easting - 500000.0
    y = northing - 10000000.0  # Hemisferio Sur

    M = y / k0
    mu = M / (a * (1 - e**2 / 4 - 3 * e**4 / 64 - 5 * e**6 / 256))

    e1 = (1 - math.sqrt(1 - e**2)) / (1 + math.sqrt(1 - e**2))
    phi1 = (
        mu
        + (3 * e1 / 2 - 27 * e1**3 / 32) * math.sin(2 * mu)
        + (21 * e1**2 / 16 - 55 * e1**4 / 32) * math.sin(4 * mu)
        + (151 * e1**3 / 96) * math.sin(6 * mu)
    )

    N1 = a / math.sqrt(1 - e**2 * math.sin(phi1) ** 2)
    T1 = math.tan(phi1) ** 2
    C1 = e_prime_sq * math.cos(phi1) ** 2
    R1 = a * (1 - e**2) / (1 - e**2 * math.sin(phi1) ** 2) ** 1.5
    D = x / (N1 * k0)

    lat = phi1 - (N1 * math.tan(phi1) / R1) * (
        D**2 / 2
        - (5 + 3 * T1 + 10 * C1 - 4 * C1**2 - 9 * e_prime_sq) * D**4 / 24
        + (61 + 90 * T1 + 298 * C1 + 45 * T1**2 - 252 * e_prime_sq - 3 * C1**2) * D**6 / 720
    )
    lon = math.radians(cm) + (
        D
        - (1 + 2 * T1 + C1) * D**3 / 6
        + (5 - 2 * C1 + 28 * T1 - 3 * C1**2 + 8 * e_prime_sq + 24 * T1**2) * D**5 / 120
    ) / math.cos(phi1)

    return round(math.degrees(lat), 6), round(math.degrees(lon), 6)


def clean_str(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    return s.title() if s.lower() not in ["none", "null", "", "s/n", "sin nombre"] else ""


def parse_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        if isinstance(val, str):
            val = val.replace(",", ".").strip()
        v = float(val)
        return v if v > 0 else None
    except (ValueError, TypeError):
        return None


def simplify_points(points: List[Tuple[float, float]], max_points: int = 12) -> List[List[float]]:
    """Muestrea equiespaciadamente la polilínea para reducir peso cartográfico."""
    if not points:
        return []
    if len(points) <= max_points:
        return [[p[0], p[1]] for p in points]
    step = len(points) / (max_points - 1)
    indices = [int(round(i * step)) for i in range(max_points - 1)] + [len(points) - 1]
    return [[points[i][0], points[i][1]] for i in indices]


def process_canales_ciren() -> Dict[str, Any]:
    print(f"\n[+] Procesando Catastro Nacional de Canales CNR / CIREN desde {RAW_SHP}...")
    if not RAW_SHP.exists():
        raise FileNotFoundError(f"Shapefile no encontrado en {RAW_SHP}")

    sf = shapefile.Reader(str(RAW_SHP), encoding="utf-8", encodingErrors="replace")
    total_records = len(sf)
    print(f"    -> {total_records:,} canales encontrados en el Shapefile.")

    canales_list: List[Dict[str, Any]] = []
    cuencas_agg: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "cuenca_codigo": "",
        "canales_count": 0,
        "longitud_total_km": 0.0,
        "juntas_vigilancia": set(),
        "ouas": set(),
        "fuentes_hidricas": set(),
        "canales_matrices": []
    })

    for idx, shape_record in enumerate(sf.iterShapeRecords()):
        d = shape_record.record.as_dict()
        sh = shape_record.shape

        gid = d.get("gid") or (idx + 1)
        codcan = str(d.get("codcan") or "").strip()
        nomcan = clean_str(d.get("nomcan")) or f"Canal {codcan or gid}"
        fuente = clean_str(d.get("fuentehid"))
        origen = clean_str(d.get("origen"))
        tipo = clean_str(d.get("tipo_canal")) or "Distribución y Conducción"
        oua = clean_str(d.get("oua"))
        oua_tipo = clean_str(d.get("oua_tipo"))
        jv = clean_str(d.get("jv"))
        n_acc = parse_float(d.get("n_acciones"))
        porc_rev = str(d.get("porc_reves") or "").strip()

        cuenca_cod = codcan[:3] if len(codcan) >= 3 and codcan[:3].isdigit() else ""

        # Procesar geometría (polyline)
        coords_wgs84: List[Tuple[float, float]] = []
        longitud_m = 0.0

        pts = sh.points
        if pts:
            for i in range(len(pts) - 1):
                p1 = pts[i]
                p2 = pts[i + 1]
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                longitud_m += math.hypot(dx, dy)

            # Convertir puntos a WGS84
            for pt in pts:
                try:
                    lat_i, lon_i = utm_19s_to_latlon(pt[0], pt[1])
                    coords_wgs84.append((lat_i, lon_i))
                except Exception:
                    pass

        longitud_km = round(longitud_m / 1000.0, 2)
        coord_inicio = [coords_wgs84[0][0], coords_wgs84[0][1]] if coords_wgs84 else None
        coord_fin = [coords_wgs84[-1][0], coords_wgs84[-1][1]] if coords_wgs84 else None

        if sh.bbox and len(sh.bbox) == 4:
            mid_e = (sh.bbox[0] + sh.bbox[2]) / 2.0
            mid_n = (sh.bbox[1] + sh.bbox[3]) / 2.0
            lat_c, lon_c = utm_19s_to_latlon(mid_e, mid_n)
            centroide = [lat_c, lon_c]
        else:
            centroide = coord_inicio

        trazado_simplificado = simplify_points(coords_wgs84, max_points=10)

        item = {
            "id": f"canal_{codcan or gid}",
            "codigo_canal": codcan,
            "nombre": nomcan,
            "tipo_canal": tipo,
            "cuenca_codigo": cuenca_cod,
            "fuente_hidrica": fuente,
            "punto_origen": origen,
            "organizacion_usuarios": oua,
            "tipo_oua": oua_tipo,
            "junta_vigilancia": jv,
            "acciones_agua": n_acc,
            "porcentaje_revestimiento": porc_rev if porc_rev else "No informado",
            "longitud_km": longitud_km,
            "coordenadas_inicio": coord_inicio,
            "coordenadas_fin": coord_fin,
            "centroide": centroide,
            "trazado_simplificado": trazado_simplificado
        }
        canales_list.append(item)

        # Agregación por Cuenca
        if cuenca_cod:
            c_agg = cuencas_agg[cuenca_cod]
            c_agg["cuenca_codigo"] = cuenca_cod
            c_agg["canales_count"] += 1
            c_agg["longitud_total_km"] += longitud_km
            if jv:
                c_agg["juntas_vigilancia"].add(jv)
            if oua:
                c_agg["ouas"].add(oua)
            if fuente:
                c_agg["fuentes_hidricas"].add(fuente)

            if longitud_km >= 15.0 or (n_acc and n_acc >= 50):
                c_agg["canales_matrices"].append({
                    "nombre": nomcan,
                    "longitud_km": longitud_km,
                    "fuente": fuente,
                    "oua": oua,
                    "lat": centroide[0] if centroide else None,
                    "lon": centroide[1] if centroide else None
                })

    # Guardar catálogo completo
    out_file = DATA_DIR / "canales_riego_chile.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(canales_list, f, indent=2, ensure_ascii=False)
    print(f" -> Guardados {len(canales_list):,} canales de riego en {out_file}")

    # Formatear resumen por cuenca
    resumen_list = []
    for cod, val in sorted(cuencas_agg.items(), key=lambda x: x[1]["canales_count"], reverse=True):
        resumen_list.append({
            "cuenca_codigo": val["cuenca_codigo"],
            "canales_count": val["canales_count"],
            "longitud_total_km": round(val["longitud_total_km"], 2),
            "juntas_vigilancia": sorted(list(val["juntas_vigilancia"]))[:8],
            "fuentes_hidricas_principales": sorted(list(val["fuentes_hidricas"]))[:8],
            "total_ouas_asociadas": len(val["ouas"]),
            "canales_matrices_principales": sorted(val["canales_matrices"], key=lambda c: c["longitud_km"], reverse=True)[:10]
        })

    resumen_file = DATA_DIR / "canales_resumen_cuencas.json"
    with open(resumen_file, "w", encoding="utf-8") as f:
        json.dump(resumen_list, f, indent=2, ensure_ascii=False)
    print(f" -> Guardado resumen de canales para {len(resumen_list)} cuencas en {resumen_file}")

    return {
        "total_canales": len(canales_list),
        "total_cuencas_con_canales": len(resumen_list),
        "longitud_total_red_km": round(sum(r["longitud_total_km"] for r in resumen_list), 2)
    }


if __name__ == "__main__":
    res = process_canales_ciren()
    print("\nRESUMEN CATASTRO NACIONAL DE CANALES DE RIEGO (CNR / CIREN):")
    for k, v in res.items():
        print(f" - {k}: {v:,}" if isinstance(v, (int, float)) else f" - {k}: {v}")
