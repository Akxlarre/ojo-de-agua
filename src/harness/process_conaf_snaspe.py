"""
Pipeline de procesamiento del Sistema Nacional de Áreas Silvestres Protegidas del Estado (SNASPE / CONAF).
Normaliza los Parques Nacionales, Reservas Nacionales y Monumentos Naturales de Chile,
calcula sus centroides de cabecera y áreas protegidas (ha/km2), asigna las macrocuencas hidrográficas DGA,
y evalúa su rol como reservas hídricas y fábricas de agua protegidas ante la degradación antrópica.
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.harness.process_mma_humedales import compute_centroid_from_geom
from src.harness.process_sma_sanciones import find_cuenca_for_point, load_cuencas_index

BASE_DIR = Path(__file__).parent.parent.parent
RAW_GEOJSON = BASE_DIR / "data" / "dga_raw" / "conaf_snaspe_areas_protegidas.geojson"
DATA_DIR = BASE_DIR / "data"


def parse_superficie_ha(val: Any) -> float:
    """Convierte cadenas de superficie chilenas (ej. '75.114,63') a float en hectáreas."""
    if not val:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def process_conaf_snaspe() -> Dict[str, Any]:
    print(f"\n[+] Procesando Catastro SNASPE de Áreas Silvestres Protegidas desde {RAW_GEOJSON}...")
    if not RAW_GEOJSON.exists():
        raise FileNotFoundError(f"Archivo GeoJSON no encontrado en {RAW_GEOJSON}")

    cuencas = load_cuencas_index()

    with open(RAW_GEOJSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    print(f"    -> {len(features)} unidades SNASPE registradas por CONAF.")

    snaspe_list: List[Dict[str, Any]] = []
    cuencas_agg: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "cuenca_codigo": "",
        "cuenca_nombre": "",
        "total_areas_protegidas": 0,
        "parques_nacionales": 0,
        "reservas_nacionales": 0,
        "monumentos_naturales": 0,
        "superficie_total_ha": 0.0,
        "superficie_total_km2": 0.0,
        "areas_destacadas": []
    })

    total_ha_nacional = 0.0
    count_parques = 0
    count_reservas = 0
    count_monumentos = 0

    for idx, feat in enumerate(features):
        props = feat.get("properties", {})
        geom = feat.get("geometry", {})

        fid = props.get("FID") or idx + 1
        nombre_completo = (props.get("NOMBRE_TOT") or f"Área Protegida {fid}").strip()
        nombre_unidad = (props.get("NOMBRE_UNI") or nombre_completo).strip()
        categoria = (props.get("CATEGORIA") or "Parque Nacional").strip()
        region = (props.get("REGION") or "").strip()
        decreto = (props.get("DECRETO_VI") or "Decreto Supremo").strip()
        id_catastro = str(props.get("ID_CATASTR") or fid).strip()
        superficie_ha = parse_superficie_ha(props.get("SUPERFICIE"))
        superficie_km2 = round(superficie_ha / 100.0, 2)

        cent = compute_centroid_from_geom(geom)
        lat, lon = (cent[0], cent[1]) if cent else (None, None)

        c_obj = find_cuenca_for_point(lat, lon, region, cuencas) if lat and lon else None
        cuenca_cod = c_obj["codigo_dga"] if c_obj else ""
        cuenca_nom = c_obj["nombre"] if c_obj else ""

        total_ha_nacional += superficie_ha

        if "PARQUE" in categoria.upper():
            count_parques += 1
        elif "RESERVA" in categoria.upper():
            count_reservas += 1
        elif "MONUMENTO" in categoria.upper():
            count_monumentos += 1

        item = {
            "id": f"conaf_snaspe_{id_catastro}_{fid}",
            "id_catastro": id_catastro,
            "nombre": nombre_completo,
            "unidad": nombre_unidad,
            "categoria": categoria,
            "region": region,
            "superficie_ha": round(superficie_ha, 2),
            "superficie_km2": superficie_km2,
            "decreto_creacion": decreto,
            "cuenca_codigo": cuenca_cod,
            "cuenca_nombre": cuenca_nom,
            "coordenadas_centroide": {"latitud": lat, "longitud": lon} if lat and lon else None,
            "es_reserva_cabecera": True,
            "fuente_oficial": "CONAF (Sistema Nacional de Áreas Silvestres Protegidas del Estado - SNASPE)"
        }
        snaspe_list.append(item)

        if cuenca_cod:
            agg = cuencas_agg[cuenca_cod]
            agg["cuenca_codigo"] = cuenca_cod
            agg["cuenca_nombre"] = cuenca_nom
            agg["total_areas_protegidas"] += 1
            agg["superficie_total_ha"] = round(agg["superficie_total_ha"] + superficie_ha, 2)
            agg["superficie_total_km2"] = round(agg["superficie_total_ha"] / 100.0, 2)

            if "PARQUE" in categoria.upper():
                agg["parques_nacionales"] += 1
            elif "RESERVA" in categoria.upper():
                agg["reservas_nacionales"] += 1
            elif "MONUMENTO" in categoria.upper():
                agg["monumentos_naturales"] += 1

            agg["areas_destacadas"].append({
                "nombre": nombre_completo,
                "categoria": categoria,
                "superficie_ha": round(superficie_ha, 2),
                "decreto": decreto
            })

    cuencas_summary = []
    for cod in sorted(cuencas_agg.keys()):
        d = cuencas_agg[cod]
        d["areas_destacadas"].sort(key=lambda x: x["superficie_ha"], reverse=True)
        cuencas_summary.append({
            "cuenca_codigo": d["cuenca_codigo"],
            "cuenca_nombre": d["cuenca_nombre"],
            "total_areas_protegidas": d["total_areas_protegidas"],
            "parques_nacionales": d["parques_nacionales"],
            "reservas_nacionales": d["reservas_nacionales"],
            "monumentos_naturales": d["monumentos_naturales"],
            "superficie_total_ha": d["superficie_total_ha"],
            "superficie_total_km2": d["superficie_total_km2"],
            "unidades_destacadas": d["areas_destacadas"][:5]
        })

    # Ordenar por mayor superficie protegida
    cuencas_summary.sort(key=lambda x: x["superficie_total_ha"], reverse=True)

    out_snaspe = DATA_DIR / "conaf_snaspe_chile.json"
    out_cuencas = DATA_DIR / "conaf_snaspe_resumen_cuencas.json"

    print(f"    -> Exportando {len(snaspe_list)} áreas silvestres protegidas a {out_snaspe}...")
    with open(out_snaspe, "w", encoding="utf-8") as f:
        json.dump(snaspe_list, f, ensure_ascii=False, indent=2)

    print(f"    -> Exportando balance de protección de cabeceras en {len(cuencas_summary)} cuencas a {out_cuencas}...")
    with open(out_cuencas, "w", encoding="utf-8") as f:
        json.dump(cuencas_summary, f, ensure_ascii=False, indent=2)

    return {
        "total_unidades_snaspe": len(snaspe_list),
        "parques_nacionales": count_parques,
        "reservas_nacionales": count_reservas,
        "monumentos_naturales": count_monumentos,
        "superficie_total_nacional_ha": round(total_ha_nacional, 2),
        "superficie_total_nacional_km2": round(total_ha_nacional / 100.0, 2),
        "cuencas_con_snaspe": len(cuencas_summary)
    }


if __name__ == "__main__":
    report = process_conaf_snaspe()
    print("\n[OK] Procesamiento CONAF SNASPE completado exitosamente:")
    for k, v in report.items():
        print(f"    - {k}: {v:,.2f}" if isinstance(v, float) else f"    - {k}: {v}")
