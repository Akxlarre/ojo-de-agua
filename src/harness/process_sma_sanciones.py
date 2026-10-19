"""
Pipeline de procesamiento del Catastro de Procedimientos Sancionatorios e Instrumentos Ambientales
de la Superintendencia del Medio Ambiente (SMA / SNIFA - Chile).
Normaliza los procesos sancionatorios, extrae las sanciones con impacto en recursos hídricos
(D.S. 90/2000 RILES Superficiales, D.S. 46/2002 RILES Subterráneos, RCAs, Caudal Ecológico, Minería),
asigna las cuencas hidrográficas DGA mediante coordenadas espaciales WGS84, y genera los resúmenes por cuenca.
"""

import csv
import json
import math
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).parent.parent.parent
RAW_SANCIONES = BASE_DIR / "data" / "dga_raw" / "sma" / "Sancionatorios.csv"
RAW_UF = BASE_DIR / "data" / "dga_raw" / "sma" / "UF_Instrumentos.csv"
CUENCAS_JSON = BASE_DIR / "data" / "cuencas_dga_chile.json"
DATA_DIR = BASE_DIR / "data"


def load_cuencas_index() -> List[Dict[str, Any]]:
    """Carga las 90 cuencas DGA y precalcula los centroides de sus bounding boxes."""
    if not CUENCAS_JSON.exists():
        return []
    with open(CUENCAS_JSON, "r", encoding="utf-8") as f:
        cuencas = json.load(f)
    for c in cuencas:
        b = c.get("bbox", {})
        c["cent_lat"] = (b.get("lat_min", 0.0) + b.get("lat_max", 0.0)) / 2.0
        c["cent_lon"] = (b.get("lon_min", 0.0) + b.get("lon_max", 0.0)) / 2.0
    return cuencas


def find_cuenca_for_point(lat: Optional[float], lon: Optional[float], region: str, cuencas: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Asigna la cuenca hidrográfica DGA óptima a una coordenada (WGS84)."""
    if lat is None or lon is None or not cuencas:
        return None
    matches = []
    for c in cuencas:
        b = c.get("bbox", {})
        if b.get("lat_min", -90) <= lat <= b.get("lat_max", 90) and b.get("lon_min", -180) <= lon <= b.get("lon_max", 180):
            dist = math.hypot(lat - c["cent_lat"], lon - c["cent_lon"])
            reg_match = (region and region.lower() in c.get("region", "").lower()) or (c.get("region", "").lower() in (region or "").lower())
            score = dist - (1.0 if reg_match else 0.0)
            matches.append((score, c))
    
    if matches:
        matches.sort(key=lambda x: x[0])
        return matches[0][1]
    
    # Fallback al centroide más próximo
    all_candidates = []
    for c in cuencas:
        dist = math.hypot(lat - c["cent_lat"], lon - c["cent_lon"])
        reg_match = bool(region and region.lower() in c.get("region", "").lower())
        all_candidates.append((dist if not reg_match else dist * 0.5, c))
    all_candidates.sort(key=lambda x: x[0])
    return all_candidates[0][1] if all_candidates else None


def process_sma_sanciones() -> Dict[str, Any]:
    print(f"\n[+] Procesando Sanciones Ambientales de la SMA desde {RAW_SANCIONES}...")
    if not RAW_SANCIONES.exists():
        raise FileNotFoundError(f"Archivo de sanciones no encontrado en {RAW_SANCIONES}")

    cuencas = load_cuencas_index()

    # 1. Cargar instrumentos de Unidades Fiscalizables (UF)
    uf_instruments = defaultdict(list)
    uf_water_tags = defaultdict(set)

    if RAW_UF.exists():
        print(f"    -> Analizando instrumentos ambientales desde {RAW_UF}...")
        with open(RAW_UF, "r", encoding="latin-1", errors="ignore") as f:
            reader = csv.DictReader(f, delimiter=";")
            for r in reader:
                uf_id = (r.get("UnidadFiscalizableId") or "").strip()
                if not uf_id:
                    continue
                corta = (r.get("DescripcionCorta") or "").strip()
                larga = (r.get("DescripcionLarga") or "").strip()
                sigla = (r.get("SiglaInstrumento") or "").strip()
                link_doc = (r.get("LinkDocumentoExterno") or "").strip()
                
                uf_instruments[uf_id].append({
                    "sigla": sigla,
                    "corta": corta,
                    "larga": larga,
                    "link": link_doc
                })
                
                full_text = f"{corta} {larga}".lower()
                if "90/2000" in full_text or "90-2000" in full_text:
                    uf_water_tags[uf_id].add("DS_90_RILES_SUPERFICIALES")
                if "46/2002" in full_text or "46-2002" in full_text:
                    uf_water_tags[uf_id].add("DS_46_RILES_SUBTERRANEAS")
                if any(w in full_text for w in ["calidad de agua", "norma secundaria", "cuenca"]):
                    uf_water_tags[uf_id].add("NORMA_CALIDAD_AGUA")
                if any(w in full_text for w in ["tratamiento de riles", "planta de tratamiento", "aguas servidas", "caudal ecológico", "glaciar"]):
                    uf_water_tags[uf_id].add("COMPROMISO_HIDRICO_RCA")

    # 2. Procesar procedimientos sancionatorios
    sanciones_list: List[Dict[str, Any]] = []
    cuencas_agg: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "cuenca_codigo": "",
        "cuenca_nombre": "",
        "total_sanciones": 0,
        "total_multa_uta": 0.0,
        "sanciones_agua": 0,
        "sectores": defaultdict(int),
        "casos_destacados": []
    })

    total_multas_nacional_uta = 0.0
    total_sanciones_agua = 0

    with open(RAW_SANCIONES, "r", encoding="latin-1", errors="ignore") as f:
        reader = csv.DictReader(f, delimiter=";")
        for r in reader:
            ps_id = (r.get("ProcesoSancionId") or "").strip()
            exp = (r.get("Expediente") or "").strip()
            tipo = (r.get("ProcesoSancionTipoNombre") or "").strip()
            estado = (r.get("ProcesoSancionEstado") or "").strip()
            f_ini = (r.get("FechaInicio") or "").strip()
            f_ter = (r.get("FechaTermino") or "").strip()
            conf_pdc = (r.get("ConfirmaPdC") or "").strip()
            
            multa_raw = (r.get("MultaTotalUTA") or "").strip()
            try:
                multa_uta = round(float(multa_raw), 2) if multa_raw else 0.0
            except ValueError:
                multa_uta = 0.0
                
            link_snifa = (r.get("LinkSNIFA") or "").strip()
            uf_id = (r.get("UnidadFiscalizableId") or "").strip()
            nombre = (r.get("Nombre") or "").strip()
            region = (r.get("RegionNombre") or "").strip()
            comuna = (r.get("ComunaNombre") or "").strip()
            
            lat_raw = (r.get("Latitud") or "").strip().replace(",", ".")
            lon_raw = (r.get("Longitud") or "").strip().replace(",", ".")
            try:
                lat = float(lat_raw)
                lon = float(lon_raw)
            except ValueError:
                lat, lon = None, None
                
            cat = (r.get("CategoriaEconomicaNombre") or "").strip()
            subcat = (r.get("SubCategoriaEconomicaNombre") or "").strip()
            
            # Asignación espacial a cuenca hidrográfica DGA
            c_obj = find_cuenca_for_point(lat, lon, region, cuencas)
            cuenca_cod = c_obj["codigo_dga"] if c_obj else ""
            cuenca_nom = c_obj["nombre"] if c_obj else ""
            
            # Relevancia hídrica e infraccional
            water_tags = sorted(list(uf_water_tags.get(uf_id, [])))
            is_water_sector = cat in ["Minería", "Agroindustrias", "Saneamiento Ambiental", "Pesca y Acuicultura", "Energía"]
            es_relevante_agua = len(water_tags) > 0 or is_water_sector
            
            total_multas_nacional_uta += multa_uta
            if es_relevante_agua:
                total_sanciones_agua += 1

            item = {
                "id": f"sma_sancion_{ps_id}",
                "proceso_sancion_id": ps_id,
                "expediente": exp,
                "tipo_procedimiento": tipo,
                "estado": estado,
                "fecha_inicio": f_ini,
                "fecha_termino": f_ter,
                "confirma_pdc": conf_pdc,
                "multa_total_uta": multa_uta,
                "link_snifa": link_snifa,
                "unidad_fiscalizable_id": uf_id,
                "unidad_fiscalizable_nombre": nombre,
                "region": region,
                "comuna": comuna,
                "coordenadas": {"latitud": lat, "longitud": lon} if lat and lon else None,
                "categoria_economica": cat,
                "subcategoria_economica": subcat,
                "cuenca_codigo": cuenca_cod,
                "cuenca_nombre": cuenca_nom,
                "es_relevante_agua": es_relevante_agua,
                "etiquetas_hidricas": water_tags,
                "instrumentos_ambientales": uf_instruments.get(uf_id, [])[:5]
            }
            sanciones_list.append(item)

            if cuenca_cod:
                agg = cuencas_agg[cuenca_cod]
                agg["cuenca_codigo"] = cuenca_cod
                agg["cuenca_nombre"] = cuenca_nom
                agg["total_sanciones"] += 1
                agg["total_multa_uta"] = round(agg["total_multa_uta"] + multa_uta, 2)
                if es_relevante_agua:
                    agg["sanciones_agua"] += 1
                agg["sectores"][cat] += 1
                
                if multa_uta >= 100.0 or len(agg["casos_destacados"]) < 3:
                    agg["casos_destacados"].append({
                        "expediente": exp,
                        "unidad": nombre,
                        "multa_uta": multa_uta,
                        "estado": estado,
                        "sector": cat
                    })

    # Convertir resumen por cuenca a lista estructurada
    cuencas_summary_list = []
    for cod in sorted(cuencas_agg.keys()):
        d = cuencas_agg[cod]
        d["casos_destacados"].sort(key=lambda x: x["multa_uta"], reverse=True)
        cuencas_summary_list.append({
            "cuenca_codigo": d["cuenca_codigo"],
            "cuenca_nombre": d["cuenca_nombre"],
            "total_sanciones": d["total_sanciones"],
            "total_multa_uta": d["total_multa_uta"],
            "sanciones_agua": d["sanciones_agua"],
            "distribucion_sectores": dict(d["sectores"]),
            "casos_destacados": d["casos_destacados"][:5]
        })

    # Guardar datasets procesados
    out_sanciones = DATA_DIR / "sma_sanciones_agua_chile.json"
    out_cuencas = DATA_DIR / "sma_resumen_cuencas.json"

    print(f"    -> Exportando {len(sanciones_list):,} sanciones a {out_sanciones}...")
    with open(out_sanciones, "w", encoding="utf-8") as f:
        json.dump(sanciones_list, f, ensure_ascii=False, indent=2)

    print(f"    -> Exportando resumen de {len(cuencas_summary_list)} cuencas a {out_cuencas}...")
    with open(out_cuencas, "w", encoding="utf-8") as f:
        json.dump(cuencas_summary_list, f, ensure_ascii=False, indent=2)

    return {
        "total_sanciones": len(sanciones_list),
        "total_sanciones_agua": total_sanciones_agua,
        "total_multas_nacional_uta": round(total_multas_nacional_uta, 2),
        "cuencas_con_sanciones": len(cuencas_summary_list)
    }


if __name__ == "__main__":
    report = process_sma_sanciones()
    print("\n[OK] Procesamiento completado:")
    for k, v in report.items():
        print(f"    - {k}: {v:,}" if isinstance(v, (int, float)) else f"    - {k}: {v}")
