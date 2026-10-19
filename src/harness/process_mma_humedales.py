"""
Pipeline de procesamiento del Inventario Nacional de Humedales Urbanos Declarados
del Ministerio del Medio Ambiente (MMA - Chile, Ley N° 21.202).
Calcula los centroides de los polígonos de protección ecosistémica,
asigna las cuencas hidrográficas DGA, y genera los balances de conservación hídrica urbana.
"""

import json
import math
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.harness.process_sma_sanciones import find_cuenca_for_point, load_cuencas_index

BASE_DIR = Path(__file__).parent.parent.parent
RAW_GEOJSON = BASE_DIR / "data" / "dga_raw" / "mma" / "Humedales Urbanos.geojson"
DATA_DIR = BASE_DIR / "data"


def compute_centroid_from_geom(geom: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    """Calcula el centroide aproximado (lat, lon) promediando los vértices de polígonos."""
    gtype = geom.get("type", "")
    coords = geom.get("coordinates", [])
    if not coords:
        return None

    all_pts = []
    if gtype == "Polygon":
        for ring in coords:
            for pt in ring:
                all_pts.append(pt)
    elif gtype == "MultiPolygon":
        for poly in coords:
            for ring in poly:
                for pt in ring:
                    all_pts.append(pt)
    elif gtype == "Point":
        all_pts.append(coords)

    if not all_pts:
        return None

    avg_lon = sum(p[0] for p in all_pts) / len(all_pts)
    avg_lat = sum(p[1] for p in all_pts) / len(all_pts)
    return round(avg_lat, 6), round(avg_lon, 6)


def process_mma_humedales() -> Dict[str, Any]:
    print(f"\n[+] Procesando Inventario MMA de Humedales Urbanos desde {RAW_GEOJSON}...")
    if not RAW_GEOJSON.exists():
        raise FileNotFoundError(f"Archivo GeoJSON no encontrado en {RAW_GEOJSON}")

    cuencas = load_cuencas_index()

    with open(RAW_GEOJSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    print(f"    -> {len(features)} humedales urbanos declarados bajo Ley 21.202.")

    humedales_list: List[Dict[str, Any]] = []
    cuencas_agg: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "cuenca_codigo": "",
        "cuenca_nombre": "",
        "total_humedales": 0,
        "superficie_protegida_ha": 0.0,
        "superficie_protegida_km2": 0.0,
        "comunas": set(),
        "humedales": []
    })

    total_ha_nacional = 0.0

    for idx, feat in enumerate(features):
        props = feat.get("properties", {})
        geom = feat.get("geometry", {})

        cod = (props.get("cod_humedal") or f"HU-{idx+1}").strip()
        nombre = (props.get("nombre_humedal") or f"Humedal {cod}").strip()
        region = (props.get("region") or "").strip()
        comuna = (props.get("comuna") or "").strip()
        ha = round(float(props.get("ha") or 0.0), 2)
        resolucion = (props.get("resolucion") or "").strip()
        tipo_proceso = (props.get("proceso_humedal_urbano") or "Oficio / Municipal").strip()
        url_bcn = (props.get("url_res_bcn") or "").strip()
        url_simbio = (props.get("url_simbio") or "").strip()

        cent = compute_centroid_from_geom(geom)
        lat, lon = (cent[0], cent[1]) if cent else (None, None)

        c_obj = find_cuenca_for_point(lat, lon, region, cuencas) if lat and lon else None
        cuenca_cod = c_obj["codigo_dga"] if c_obj else ""
        cuenca_nom = c_obj["nombre"] if c_obj else ""

        total_ha_nacional += ha

        item = {
            "id": f"mma_humedal_{cod.replace(' ', '_').lower()}",
            "codigo_humedal": cod,
            "nombre": nombre,
            "superficie_ha": ha,
            "superficie_km2": round(ha / 100.0, 3),
            "region": region,
            "comuna": comuna,
            "tipo_declaratoria": tipo_proceso,
            "resolucion_mma": resolucion,
            "enlace_decreto_bcn": url_bcn,
            "enlace_simbio": url_simbio,
            "cuenca_codigo": cuenca_cod,
            "cuenca_nombre": cuenca_nom,
            "coordenadas": {"latitud": lat, "longitud": lon} if lat and lon else None,
            "es_protegido_ley_21202": True
        }
        humedales_list.append(item)

        if cuenca_cod:
            agg = cuencas_agg[cuenca_cod]
            agg["cuenca_codigo"] = cuenca_cod
            agg["cuenca_nombre"] = cuenca_nom
            agg["total_humedales"] += 1
            agg["superficie_protegida_ha"] = round(agg["superficie_protegida_ha"] + ha, 2)
            agg["superficie_protegida_km2"] = round(agg["superficie_protegida_ha"] / 100.0, 3)
            agg["comunas"].add(comuna)
            agg["humedales"].append({
                "codigo": cod,
                "nombre": nombre,
                "ha": ha,
                "comuna": comuna,
                "resolucion": resolucion
            })

    cuencas_summary = []
    for cod in sorted(cuencas_agg.keys()):
        d = cuencas_agg[cod]
        d["humedales"].sort(key=lambda x: x["ha"], reverse=True)
        cuencas_summary.append({
            "cuenca_codigo": d["cuenca_codigo"],
            "cuenca_nombre": d["cuenca_nombre"],
            "total_humedales": d["total_humedales"],
            "superficie_protegida_ha": d["superficie_protegida_ha"],
            "superficie_protegida_km2": d["superficie_protegida_km2"],
            "comunas": sorted(list(d["comunas"])),
            "humedales_destacados": d["humedales"][:6]
        })

    out_humedales = DATA_DIR / "mma_humedales_chile.json"
    out_cuencas = DATA_DIR / "mma_humedales_resumen_cuencas.json"

    print(f"    -> Exportando {len(humedales_list)} humedales protegidos a {out_humedales}...")
    with open(out_humedales, "w", encoding="utf-8") as f:
        json.dump(humedales_list, f, ensure_ascii=False, indent=2)

    print(f"    -> Exportando resumen de {len(cuencas_summary)} cuencas a {out_cuencas}...")
    with open(out_cuencas, "w", encoding="utf-8") as f:
        json.dump(cuencas_summary, f, ensure_ascii=False, indent=2)

    return {
        "total_humedales_urbanos": len(humedales_list),
        "superficie_total_protegida_ha": round(total_ha_nacional, 2),
        "superficie_total_protegida_km2": round(total_ha_nacional / 100.0, 3),
        "cuencas_con_humedales": len(cuencas_summary)
    }


if __name__ == "__main__":
    report = process_mma_humedales()
    print("\n[OK] Procesamiento MMA completado:")
    for k, v in report.items():
        print(f"    - {k}: {v:,}" if isinstance(v, (int, float)) else f"    - {k}: {v}")
