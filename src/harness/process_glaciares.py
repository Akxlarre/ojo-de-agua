"""
Pipeline de procesamiento del Inventario Público de Glaciares de Chile (DGA - IPG 2022).
Extrae los 26.180 glaciares oficiales desde el Shapefile oficial, normaliza sus atributos
hidrológicos y criosféricos, y genera los datasets consolidados para el Grafo de Conocimiento y API.
"""

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List
import shapefile

BASE_DIR = Path(__file__).parent.parent.parent
RAW_DIR = BASE_DIR / "data" / "dga_raw" / "glaciares" / "Glaciares" / "IPG_2022_v2"
DATA_DIR = BASE_DIR / "data"


def clean_str(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    return s if s.lower() not in ["none", "null", "s/n", "sin nombre"] else ""


def parse_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        if isinstance(val, str):
            val = val.replace(",", ".").strip()
        return float(val)
    except (ValueError, TypeError):
        return default


def process_glaciares() -> Dict[str, Any]:
    shp_path = RAW_DIR / "INV_PG_2022_v2.shp"
    print(f"\n[+] Procesando Inventario Público de Glaciares desde {shp_path}...")
    if not shp_path.exists():
        raise FileNotFoundError(f"Shapefile no encontrado en {shp_path}")

    sf = shapefile.Reader(str(shp_path), encoding="utf-8", encodingErrors="replace")
    total_records = len(sf)
    print(f"    -> {total_records:,} registros encontrados en el Shapefile.")

    glaciares_list: List[Dict[str, Any]] = []
    cuencas_agg: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "cuenca_codigo": "",
        "cuenca_nombre": "",
        "glaciares_count": 0,
        "superficie_total_km2": 0.0,
        "volumen_total_km3": 0.0,
        "equivalente_agua_total_km3": 0.0,
        "tipos_desglose": defaultdict(int),
        "glaciares_principales": []
    })

    for idx, shape_record in enumerate(sf.iterShapeRecords()):
        d = shape_record.record.as_dict()
        sh = shape_record.shape

        cod_gla = clean_str(d.get("COD_GLA")) or f"GLA_{idx+1}"
        nom_gla = clean_str(d.get("NOM_GLA") or d.get("NOMBRE"))
        display_name = nom_gla if nom_gla else f"Glaciar {cod_gla}"
        clasifica = clean_str(d.get("CLASIFICA")) or "GLACIARETE"
        cod_cuen = clean_str(d.get("COD_CUEN"))
        nom_cuen = clean_str(d.get("NOM_CUEN"))
        region = clean_str(d.get("REGION"))
        comuna = clean_str(d.get("COMUNA"))
        orienta = clean_str(d.get("ORIENTA"))

        area_km2 = parse_float(d.get("AREA_KM2"))
        vol_km3 = parse_float(d.get("VOL_KM3"))
        eq_agua_km3 = parse_float(d.get("EQ_AGUAKM3"))
        esp_med = parse_float(d.get("ESP_MED"))
        hmedia = parse_float(d.get("HMEDIA"))
        hmin = parse_float(d.get("HMIN"))
        hmax = parse_float(d.get("HMAX"))

        # Determinar coordenadas (centroide oficial o fallback a bbox)
        lat_rec = parse_float(d.get("LATITUD"))
        lon_rec = parse_float(d.get("LONGITUD"))
        if lat_rec != 0.0 and lon_rec != 0.0:
            lat, lon = lat_rec, lon_rec
        elif sh.bbox:
            lat = (sh.bbox[1] + sh.bbox[3]) / 2.0
            lon = (sh.bbox[0] + sh.bbox[2]) / 2.0
        else:
            lat, lon = 0.0, 0.0

        item = {
            "id": f"glaciar_{cod_gla.replace('@', '')}",
            "codigo_glaciar": cod_gla,
            "nombre": display_name,
            "nombre_oficial": nom_gla if nom_gla else None,
            "clasificacion": clasifica,
            "area_km2": round(area_km2, 4),
            "volumen_km3": round(vol_km3, 4),
            "equivalente_agua_km3": round(eq_agua_km3, 4),
            "espesor_medio_m": round(esp_med, 1),
            "elevacion_media_msnm": round(hmedia, 1),
            "elevacion_min_msnm": round(hmin, 1),
            "elevacion_max_msnm": round(hmax, 1),
            "orientacion": orienta,
            "cuenca_codigo": cod_cuen,
            "cuenca_nombre": nom_cuen,
            "region": region,
            "comuna": comuna,
            "coordenadas": [round(lat, 6), round(lon, 6)],
            "proteccion_legal": "Art. 5 bis Ley 21.435 (Reserva Crioclimática Intocable)"
        }
        glaciares_list.append(item)

        # Agregación por Cuenca
        if cod_cuen:
            c_data = cuencas_agg[cod_cuen]
            c_data["cuenca_codigo"] = cod_cuen
            c_data["cuenca_nombre"] = nom_cuen
            c_data["glaciares_count"] += 1
            c_data["superficie_total_km2"] += area_km2
            c_data["volumen_total_km3"] += vol_km3
            c_data["equivalente_agua_total_km3"] += eq_agua_km3
            c_data["tipos_desglose"][clasifica] += 1

            if area_km2 >= 1.0 or nom_gla:
                c_data["glaciares_principales"].append({
                    "nombre": display_name,
                    "area_km2": round(area_km2, 2),
                    "volumen_km3": round(vol_km3, 3),
                    "tipo": clasifica,
                    "lat": round(lat, 4),
                    "lon": round(lon, 4)
                })

    # Guardar glaciares completos
    out_file = DATA_DIR / "glaciares_chile.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(glaciares_list, f, indent=2, ensure_ascii=False)
    print(f" -> Guardados {len(glaciares_list):,} glaciares en {out_file}")

    # Formatear resumen por cuenca
    resumen_list = []
    for cod, val in sorted(cuencas_agg.items(), key=lambda x: x[1]["superficie_total_km2"], reverse=True):
        val["superficie_total_km2"] = round(val["superficie_total_km2"], 2)
        val["volumen_total_km3"] = round(val["volumen_total_km3"], 3)
        val["equivalente_agua_total_km3"] = round(val["equivalente_agua_total_km3"], 3)
        val["tipos_desglose"] = dict(val["tipos_desglose"])
        val["glaciares_principales"] = sorted(val["glaciares_principales"], key=lambda g: g["area_km2"], reverse=True)[:10]
        resumen_list.append(val)

    resumen_file = DATA_DIR / "glaciares_resumen_cuencas.json"
    with open(resumen_file, "w", encoding="utf-8") as f:
        json.dump(resumen_list, f, indent=2, ensure_ascii=False)
    print(f" -> Guardado resumen de reservas criosféricas para {len(resumen_list)} cuencas en {resumen_file}")

    return {
        "total_glaciares": len(glaciares_list),
        "total_cuencas_con_glaciares": len(resumen_list),
        "superficie_total_nacional_km2": round(sum(r["superficie_total_km2"] for r in resumen_list), 2),
        "volumen_total_nacional_km3": round(sum(r["volumen_total_km3"] for r in resumen_list), 2)
    }


if __name__ == "__main__":
    res = process_glaciares()
    print("\nRESUMEN CATASTRO NACIONAL DE GLACIARES (IPG 2022 - DGA):")
    for k, v in res.items():
        print(f" - {k}: {v:,}" if isinstance(v, (int, float)) else f" - {k}: {v}")
