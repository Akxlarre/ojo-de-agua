"""
Pipeline de procesamiento del Catastro de Plantas de Tratamiento de Aguas Servidas (PTAS)
y puntos de descarga de la Superintendencia de Servicios Sanitarios (SISS - Chile).
Estructura las plantas sanitarias urbanas, identifica los cuerpos receptores (ríos, esteros, riego, mar),
asigna las cuencas hidrográficas DGA mediante coordenadas espaciales WGS84,
y consolida los balances de saneamiento urbano por macrocuenca.
"""

import json
import math
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import shapefile

from src.harness.process_sma_sanciones import find_cuenca_for_point, load_cuencas_index

BASE_DIR = Path(__file__).parent.parent.parent
RAW_SHP = BASE_DIR / "data" / "dga_raw" / "siss" / "PTAS_PTODESCARGA_Sirgas19s_VF.shp"
DATA_DIR = BASE_DIR / "data"


def clean_str(val: Any) -> str:
    if val is None:
        return ""
    return str(val).strip()


def parse_float(val: Any) -> float:
    if val is None:
        return 0.0
    try:
        return float(str(val).replace(",", ".").strip())
    except (ValueError, TypeError):
        return 0.0


def process_siss_sanitarias() -> Dict[str, Any]:
    print(f"\n[+] Procesando Catastro SISS de Plantas de Tratamiento de Aguas Servidas desde {RAW_SHP}...")
    if not RAW_SHP.exists():
        raise FileNotFoundError(f"Shapefile no encontrado en {RAW_SHP}")

    cuencas = load_cuencas_index()
    sf = shapefile.Reader(str(RAW_SHP), encoding="utf-8", encodingErrors="replace")
    total_records = len(sf)
    print(f"    -> {total_records} instalaciones y descargas encontradas.")

    plantas_list: List[Dict[str, Any]] = []
    cuencas_agg: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "cuenca_codigo": "",
        "cuenca_nombre": "",
        "total_plantas": 0,
        "empresas_sanitarias": set(),
        "sistemas_urbanos": set(),
        "tipos_receptores": defaultdict(int),
        "plantas_destacadas": []
    })

    empresas_nacionales = set()

    for idx, shape_record in enumerate(sf.iterShapeRecords()):
        d = shape_record.record.as_dict()
        sh = shape_record.shape

        empresa = clean_str(d.get("EMPRESA"))
        sistema = clean_str(d.get("SISTEMA"))
        cod_obra = clean_str(d.get("COD_OBRA")) or f"OBRA-{idx+1}"
        nom_obra = clean_str(d.get("NOM_OBRA")) or f"PTAS {sistema}"
        ano_const = int(d.get("ANO_CONST") or 0)
        estado = clean_str(d.get("ESTADO_USO")) or "EN_OPERACION"
        receptor = clean_str(d.get("RECEPTOR"))
        tipo_rec = clean_str(d.get("TIPO_RECEP")) or receptor
        region = clean_str(d.get("REGION"))
        rut = clean_str(d.get("RUT"))

        empresas_nacionales.add(empresa)

        # Coordenadas geográficas WGS84
        coords = None
        lat, lon = None, None
        if sh.points and len(sh.points) >= 1:
            lon_p, lat_p = sh.points[0]
            if -56.0 <= lat_p <= -17.0 and -76.0 <= lon_p <= -66.0:
                lat, lon = round(lat_p, 6), round(lon_p, 6)
                coords = {"latitud": lat, "longitud": lon}

        # Asignar Cuenca DGA
        c_obj = find_cuenca_for_point(lat, lon, region, cuencas) if lat and lon else None
        cuenca_cod = c_obj["codigo_dga"] if c_obj else ""
        cuenca_nom = c_obj["nombre"] if c_obj else ""

        # Clasificación simplificada del cuerpo receptor
        rec_lower = receptor.lower()
        if "rio" in rec_lower or "estero" in rec_lower or "canal" in rec_lower or "quebrada" in rec_lower:
            categoria_receptor = "Cauce Natural Superficial (Río / Estero)"
        elif "mar" in rec_lower or "emisario" in rec_lower or "oceano" in rec_lower or "bahia" in rec_lower:
            categoria_receptor = "Emisario Submarino / Marino"
        elif "riego" in rec_lower:
            categoria_receptor = "Reúso en Riego Agrícola"
        elif "infiltra" in rec_lower or "suelo" in rec_lower or "terreno" in rec_lower:
            categoria_receptor = "Infiltración al Suelo"
        else:
            categoria_receptor = "Descarga Terrestre / Otros"

        item = {
            "id": f"siss_ptas_{cod_obra}",
            "codigo_obra": cod_obra,
            "nombre": nom_obra,
            "empresa_concesionaria": empresa,
            "rut_empresa": rut,
            "sistema_urbano": sistema,
            "ano_construccion": ano_const,
            "estado_operativo": estado,
            "cuerpo_receptor": receptor,
            "tipo_receptor": tipo_rec,
            "categoria_receptor": categoria_receptor,
            "region": region,
            "cuenca_codigo": cuenca_cod,
            "cuenca_nombre": cuenca_nom,
            "coordenadas": coords
        }
        plantas_list.append(item)

        if cuenca_cod:
            agg = cuencas_agg[cuenca_cod]
            agg["cuenca_codigo"] = cuenca_cod
            agg["cuenca_nombre"] = cuenca_nom
            agg["total_plantas"] += 1
            agg["empresas_sanitarias"].add(empresa)
            agg["sistemas_urbanos"].add(sistema)
            agg["tipos_receptores"][categoria_receptor] += 1
            if len(agg["plantas_destacadas"]) < 6:
                agg["plantas_destacadas"].append({
                    "nombre": nom_obra,
                    "empresa": empresa,
                    "sistema": sistema,
                    "receptor": receptor,
                    "categoria": categoria_receptor
                })

    # Consolidar resumen de cuencas
    cuencas_summary = []
    for cod in sorted(cuencas_agg.keys()):
        d = cuencas_agg[cod]
        cuencas_summary.append({
            "cuenca_codigo": d["cuenca_codigo"],
            "cuenca_nombre": d["cuenca_nombre"],
            "total_plantas": d["total_plantas"],
            "empresas_sanitarias": sorted(list(d["empresas_sanitarias"])),
            "sistemas_urbanos_count": len(d["sistemas_urbanos"]),
            "distribucion_receptores": dict(d["tipos_receptores"]),
            "plantas_destacadas": d["plantas_destacadas"]
        })

    # Guardar archivos procesados
    out_plantas = DATA_DIR / "siss_plantas_chile.json"
    out_cuencas = DATA_DIR / "siss_resumen_cuencas.json"

    print(f"    -> Exportando {len(plantas_list)} plantas PTAS a {out_plantas}...")
    with open(out_plantas, "w", encoding="utf-8") as f:
        json.dump(plantas_list, f, ensure_ascii=False, indent=2)

    print(f"    -> Exportando resumen de {len(cuencas_summary)} cuencas a {out_cuencas}...")
    with open(out_cuencas, "w", encoding="utf-8") as f:
        json.dump(cuencas_summary, f, ensure_ascii=False, indent=2)

    return {
        "total_plantas_ptas": len(plantas_list),
        "empresas_sanitarias": len(empresas_nacionales),
        "cuencas_con_plantas": len(cuencas_summary)
    }


if __name__ == "__main__":
    report = process_siss_sanitarias()
    print("\n[OK] Procesamiento SISS completado:")
    for k, v in report.items():
        print(f"    - {k}: {v}")
