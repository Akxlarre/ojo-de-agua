"""
Pipeline de procesamiento del Catastro Público de Aguas (CPA - DGA Chile).
Procesa los 159.960 derechos de aprovechamiento de aguas (DAA) constituidos en Chile:
- Consuntivos y No Consuntivos
- Superficiales y Subterráneos
- Permanentes, Eventuales y Continuos
Estructura la volumetría por Cuenca DGA, convierte coordenadas UTM a WGS84,
y genera los resúmenes agregados y los derechos estratégicos para el Semantic Knowledge Graph.
"""

import json
import math
import os
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
from src.harness.process_canales_ciren import utm_19s_to_latlon

BASE_DIR = Path(__file__).parent.parent.parent
RAW_CPA = BASE_DIR / "data" / "dga_raw" / "cpa" / "DerechosConcedidos.xlsx"
CUENCAS_JSON = BASE_DIR / "data" / "cuencas_dga_chile.json"
DATA_DIR = BASE_DIR / "data"

# Mapeo exhaustivo de los nombres de cuenca del CPA al código DGA de 3 dígitos
CPA_CUENCA_MAP = {
    'Rio Maipo': '057',
    'Rio Bueno': '103',
    'Rio Maule': '073',
    'Rio Itata': '081',
    'Rio Imperial': '091',
    'Rio Rapel': '060',
    'Rio Valdivia': '101',
    'Rio Tolten': '094',
    'Cuencas e Islas entre R.Bueno y R. Puelo': '104',
    'Rio Bio-Bio': '083',
    'Rio Limari': '045',
    'Rio Aconcagua': '054',
    'Rio Aisen': '113',
    'Rio Ligua': '052',
    'Islas Chiloe y Circundantes': '109',
    'Rio Mataquito': '071',
    'Costeras entre Aconcagua y Maipo': '055',
    'Rio Elqui': '043',
    'Rio Petorca': '051',
    'Rio Choapa': '047',
    'Costeras Rapel-E.Nilahue': '061',
    'Rio Baker': '115',
    'Pampa del Tamarugal': '019',
    'Costeras Lebu-Paicavi': '085',
    'R.  Copiapo': '030',
    'Costeras Ligua-Aconcagua': '053',
    'Costeras entre Elqui y Limari': '044',
    'Costeras entre R.Puelo y R.Yelcho': '106',
    'Rio Lluta': '010',
    'Costeras entre  Maipo y Rapel': '058',
    'Altiplanicas': '017',
    'Costeras e Islas entre Rio Itata y Rio Bio-Bio': '082',
    'Costeras e Islas entre R.Paicavi y Limite Region': '085',
    'Costeras entre limite Region y R.Valdivia': '102',
    'Rio San Jose': '013',
    'Costeras entre Lag.  Blanca(inc), Seno Otway, canal Jeronimo y Magallanes': '124',
    'Rio Huasco': '034',
    'Costeras e Islas entre R.Palena y R.Aisen': '112',
    'Costeras entre limite Region y R. Itata': '074',
    'Rio Loa': '021',
    'Rio Palena y Costeras Limite Decima Region': '110',
    'Tierra del Fuego': '125',
    'Rio Quilimari': '048',
    'Costeras Carampangue-Lebu': '085',
    'Costeras Maule y Limite Region': '074',
    'Costeras entre R.Valdivia y R.Bueno': '102',
    'Costeras entre Seno Andrew y R. Hollemberg e islas al oriente': '122',
    'Rio Puelo': '107',
    'Rio Queule': '094',
    'Rio Budi': '093',
    'Rio Yelcho': '108',
    'Rio Carampangue': '084',
    'Costeras e Islas entre R Hollemberg, Golfo Alte. Laguna Blanca': '124',
    'Costeras R. San Jose-Q.Camarones': '014',
    'Salar de Atacama': '024',
    'Costeras entre R.Limari y R.Choapa': '046',
    'Costeras e Islas entre Rios Bio-Bio y Carampangue': '084',
    'Rio Lebu': '085',
    'Costeras e Islas entre R Aisen y R Baker y Canal Gral. Martinez': '114',
    'Rio los Choros': '041',
    'Costeras entre R.Choapa y R.Quilimari': '048',
    'Rio Pascua': '117',
    'Q. Rio Camarones': '015',
    'Quebrada Carrizal y Costeras hasta R. Huasco': '036',
    'Costeras Quilimari-Petorca': '048',
    'Costeras Entre Rio Budi y Rio Tolten': '093',
    'Archipielagos de Las Guaitecas y de los Chonos': '111',
    'Vertiente del Atlantico': '128',
    'Costeras R.Camarones-Pampa del Tamarugal': '018',
    'Costeras entre limite Region y R.  Mataquito': '071',
    'Costeras Mataquito-Maule': '072',
    'Quebrada la Negra': '026',
    'Endorreicas entre Frontera y Vertiente del Pacifico': '025',
    'Endorreicas Salar Atacama-Vertiente Pacifico': '025',
    'Quebrada Caracoles': '023',
    'Islas al sur del Canal Beagle y Territorio Antartico': '127',
    'Costeras Limite Region y R.  Imperial': '092',
    'Fronterizas Salar Michincha-R.Loa': '020',
    'Costeras entrre R. Los Choros y R. Elqui': '042',
    'Rio Salado': '032',
    'Costeras entre Q. la Negra y Q. Pan de Azucar': '031',
    'Costeras e Islas entre R.Huasco y Cuarta Region': '037',
    'Q.Totoral y Costeras hasta Q.Carrizal': '035',
    'Costeras entre R.Yelcho y limite Regional': '108',
    'Costeras entre R. Pascua Limite Region. Archipielago Guayeco': '118',
    'Endorreica entre Fronterizas y Salar Atacama': '022',
    'Quebrada de la Concordia': '012',
    'Costeras e Islas entre R. Baker y R. Pascua': '116',
    'Costeras R.Loa-Q.Caracoles': '022',
    'Islas entre limite Region y Canal Ancho y Estrecho de la Concepcion': '120',
    'Costeras Tilviche-Loa': '020',
    'Costeras Q.Pan de Azucar-R.Salado': '031',
    'Costeras e Islas R.Salado-R.Copiapo': '033',
    'Islas del Pacifico': '056',
    'Costeras e Islas entre Tercera Region y Q. Los Choros': '039',
    'Costeras entre R.Copiapo y Q.Totoral': '035',
    'Costeras entre Limite Region y Seno Andrew': '120',
    'Fronterizas Salares Atacama-Socompa': '025',
    'Islas al Sur Estrecho de Magallanes': '127'
}


def clean_str(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    return s if s.lower() not in ["none", "null", "", "(0-0-0)"] else ""


def parse_float(val: Any) -> float:
    if val is None:
        return 0.0
    try:
        s = str(val).replace(",", ".").strip()
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def parse_caudal_lps(val: Any, unit: Any) -> float:
    raw = parse_float(val)
    if raw <= 0:
        return 0.0
    u = str(unit or "").lower().strip()
    if "m3/s" in u or "m3/seg" in u or "metro" in u:
        return round(raw * 1000.0, 3)
    # Default is L/s o Lt/s
    return round(raw, 3)


def parse_utm_coords(norte_val: Any, este_val: Any) -> Optional[Tuple[float, float]]:
    n = parse_float(norte_val)
    e = parse_float(este_val)
    if n <= 0 or e <= 0:
        return None
    # Fix scaling error if numbers are in millimeters
    if n > 1000000000:
        n /= 1000.0
        e /= 1000.0
    # Chile continental UTM ranges
    if 4000000 <= n <= 8500000 and 150000 <= e <= 850000:
        try:
            lat, lon = utm_19s_to_latlon(e, n)
            if -56.0 <= lat <= -17.0 and -76.0 <= lon <= -66.0:
                return round(lat, 6), round(lon, 6)
        except Exception:
            return None
    return None


def process_cpa_derechos() -> Dict[str, Any]:
    print(f"\n[+] Procesando Catastro Público de Aguas (CPA) desde {RAW_CPA}...")
    if not RAW_CPA.exists():
        raise FileNotFoundError(f"Archivo CPA no encontrado en {RAW_CPA}")

    # Cargar catálogo de cuencas oficiales
    with open(CUENCAS_JSON, "r", encoding="utf-8") as f:
        cuencas_dga = json.load(f)
    cuencas_info = {c["codigo_dga"]: c["nombre"] for c in cuencas_dga}

    wb = openpyxl.load_workbook(str(RAW_CPA), read_only=True, data_only=True)
    ws = wb.active

    cuencas_agg: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "cuenca_codigo": "",
        "cuenca_nombre": "",
        "total_derechos": 0,
        "caudal_consuntivo_total_lps": 0.0,
        "caudal_no_consuntivo_total_lps": 0.0,
        "derechos_consuntivos": 0,
        "derechos_no_consuntivos": 0,
        "derechos_subterraneos": 0,
        "derechos_superficiales": 0,
        "derechos_permanentes": 0,
        "derechos_eventuales": 0,
        "titulares_caudal": defaultdict(float),
        "distribucion_usos": defaultdict(int),
        "titulos_destacados": []
    })

    derechos_destacados: List[Dict[str, Any]] = []

    total_scanned = 0
    total_consuntivo_nacional_lps = 0.0
    total_no_consuntivo_nacional_lps = 0.0
    start_t = time.time()

    for idx, row in enumerate(ws.iter_rows(values_only=True)):
        if idx < 7:  # Filas de encabezado
            continue

        total_scanned += 1
        num_reg = row[0]
        exp = clean_str(row[1]) or f"EXP-{idx}"
        sol_n = row[2] or 1
        region = clean_str(row[3])
        provincia = clean_str(row[4])
        comuna = clean_str(row[5])
        titular = clean_str(row[6])
        f_res = clean_str(row[8])
        num_res = clean_str(row[9])
        
        tipo_der = clean_str(row[12])  # Consuntivo / No Consuntivo
        nat_agua = clean_str(row[13])  # Superficial y Corriente / Subterranea
        fuente_clas = clean_str(row[14])
        uso = clean_str(row[15]) or "No Especificado"
        cpa_cuenca_str = clean_str(row[16])
        fuente_nom = clean_str(row[19])
        
        ejercicio = clean_str(row[32])  # Permanente y Continuo, Eventual, etc.
        caudal_raw = row[33]
        unidad_raw = row[34]
        caudal_lps = parse_caudal_lps(caudal_raw, unidad_raw)
        volumen_m3 = parse_float(row[40])
        
        # Mapeo a Cuenca DGA
        cuenca_cod = CPA_CUENCA_MAP.get(cpa_cuenca_str, "")
        if not cuenca_cod and len(exp) >= 7:
            # Fallback a código en expediente ej ND-0570-12 -> 057
            num_match = re.search(r'([0-9]{3,4})', exp)
            if num_match:
                cand = num_match.group(1)[:3]
                if cand in cuencas_info:
                    cuenca_cod = cand

        cuenca_nom = cuencas_info.get(cuenca_cod, cpa_cuenca_str)

        # Georreferenciación
        coords = None
        lat_direct = parse_float(row[45])
        lon_direct = parse_float(row[46])
        if -56.0 <= lat_direct <= -17.0 and -76.0 <= lon_direct <= -66.0:
            coords = {"latitud": round(lat_direct, 6), "longitud": round(lon_direct, 6)}
        else:
            utm_c = parse_utm_coords(row[41], row[42])
            if utm_c:
                coords = {"latitud": utm_c[0], "longitud": utm_c[1]}

        is_consuntivo = "consuntivo" in tipo_der.lower() and "no consuntivo" not in tipo_der.lower()
        is_subterraneo = "subterranea" in nat_agua.lower() or "acuifero" in fuente_clas.lower()
        is_permanente = "permanente" in ejercicio.lower()

        if is_consuntivo:
            total_consuntivo_nacional_lps += caudal_lps
        else:
            total_no_consuntivo_nacional_lps += caudal_lps

        # Agregar a resumen por cuenca
        if cuenca_cod:
            agg = cuencas_agg[cuenca_cod]
            agg["cuenca_codigo"] = cuenca_cod
            agg["cuenca_nombre"] = cuenca_nom
            agg["total_derechos"] += 1
            if is_consuntivo:
                agg["caudal_consuntivo_total_lps"] = round(agg["caudal_consuntivo_total_lps"] + caudal_lps, 2)
                agg["derechos_consuntivos"] += 1
            else:
                agg["caudal_no_consuntivo_total_lps"] = round(agg["caudal_no_consuntivo_total_lps"] + caudal_lps, 2)
                agg["derechos_no_consuntivos"] += 1

            if is_subterraneo:
                agg["derechos_subterraneos"] += 1
            else:
                agg["derechos_superficiales"] += 1

            if is_permanente:
                agg["derechos_permanentes"] += 1
            else:
                agg["derechos_eventuales"] += 1

            if titular:
                agg["titulares_caudal"][titular] += caudal_lps

            # Clasificación de uso simplificada
            uso_key = "Riego" if "riego" in uso.lower() or "agricola" in uso.lower() else (
                "Bebida y Saneamiento" if any(w in uso.lower() for w in ["bebida", "domestico", "saneamiento", "potable"]) else (
                    "Minería" if "miner" in uso.lower() else (
                        "Hidroeléctrico" if any(w in uso.lower() for w in ["hidro", "energia", "generacion"]) else (
                            "Industrial" if "industr" in uso.lower() else "Otros Usos"
                        )
                    )
                )
            )
            agg["distribucion_usos"][uso_key] += 1

            # Títulos destacados por cuenca (caudal alto)
            if (is_consuntivo and caudal_lps >= 50.0) or (not is_consuntivo and caudal_lps >= 1000.0) or len(agg["titulos_destacados"]) < 5:
                agg["titulos_destacados"].append({
                    "expediente": exp,
                    "titular": titular,
                    "tipo": "Consuntivo" if is_consuntivo else "No Consuntivo",
                    "caudal_lps": caudal_lps,
                    "fuente": fuente_nom or cpa_cuenca_str,
                    "ejercicio": ejercicio
                })

        # Derechos estratégicos a nivel nacional para el Semantic Knowledge Graph
        # Criterio: Caudal consuntivo >= 80 L/s, No consuntivo >= 2000 L/s, o agua potable / minería relevante
        es_estrategico = (
            (is_consuntivo and caudal_lps >= 80.0) or
            (not is_consuntivo and caudal_lps >= 2000.0) or
            (caudal_lps >= 25.0 and any(w in titular.lower() for w in ["aguas andinas", "esval", "essbio", "essal", "codelco", "anglo", "bhp", "collahuasi", "enel", "colbun", "cge"]))
        )

        if es_estrategico and titular:
            item_destacado = {
                "id": f"daa_{exp.strip().replace(' ', '_')}_{sol_n}",
                "codigo_expediente": exp,
                "solicitud_num": sol_n,
                "titular": titular,
                "tipo_derecho": "Consuntivo" if is_consuntivo else "No Consuntivo",
                "naturaleza_agua": "Subterránea" if is_subterraneo else "Superficial",
                "ejercicio_derecho": ejercicio or "Permanente y Continuo",
                "uso_agua": uso,
                "caudal_concedido_lps": caudal_lps,
                "volumen_anual_m3": volumen_m3,
                "fuente": fuente_nom or cpa_cuenca_str,
                "cuenca_codigo": cuenca_cod,
                "cuenca_nombre": cuenca_nom,
                "region": region,
                "provincia": provincia,
                "comuna": comuna,
                "fecha_resolucion": f_res,
                "numero_resolucion": num_res,
                "coordenadas": coords
            }
            derechos_destacados.append(item_destacado)

        if total_scanned % 50000 == 0:
            print(f"    Procesados {total_scanned:,} / 159,960 registros en {time.time() - start_t:.1f}s...")

    wb.close()
    print(f"\n[OK] Análisis completado de {total_scanned:,} registros en {time.time() - start_t:.1f}s.")

    # Generar listado consolidado de cuencas
    resumen_cuencas_list = []
    for cod in sorted(cuencas_agg.keys()):
        d = cuencas_agg[cod]
        # Top 5 titulares por caudal
        top_titulares = sorted(d["titulares_caudal"].items(), key=lambda x: x[1], reverse=True)[:5]
        top_titulares_fmt = [{"titular": t[0], "caudal_total_lps": round(t[1], 2)} for t in top_titulares]
        
        # Top 5 títulos por caudal
        d["titulos_destacados"].sort(key=lambda x: x["caudal_lps"], reverse=True)

        resumen_cuencas_list.append({
            "cuenca_codigo": d["cuenca_codigo"],
            "cuenca_nombre": d["cuenca_nombre"],
            "total_derechos": d["total_derechos"],
            "caudal_consuntivo_total_lps": round(d["caudal_consuntivo_total_lps"], 2),
            "caudal_consuntivo_total_m3s": round(d["caudal_consuntivo_total_lps"] / 1000.0, 3),
            "caudal_no_consuntivo_total_lps": round(d["caudal_no_consuntivo_total_lps"], 2),
            "caudal_no_consuntivo_total_m3s": round(d["caudal_no_consuntivo_total_lps"] / 1000.0, 3),
            "derechos_consuntivos": d["derechos_consuntivos"],
            "derechos_no_consuntivos": d["derechos_no_consuntivos"],
            "derechos_subterraneos": d["derechos_subterraneos"],
            "derechos_superficiales": d["derechos_superficiales"],
            "derechos_permanentes": d["derechos_permanentes"],
            "derechos_eventuales": d["derechos_eventuales"],
            "distribucion_usos": dict(d["distribucion_usos"]),
            "principales_titulares": top_titulares_fmt,
            "titulos_destacados": d["titulos_destacados"][:5]
        })

    # Guardar datasets procesados
    out_resumen = DATA_DIR / "cpa_resumen_cuencas.json"
    out_destacados = DATA_DIR / "cpa_derechos_destacados.json"

    print(f"    -> Exportando resumen de {len(resumen_cuencas_list)} cuencas a {out_resumen}...")
    with open(out_resumen, "w", encoding="utf-8") as f:
        json.dump(resumen_cuencas_list, f, ensure_ascii=False, indent=2)

    print(f"    -> Exportando {len(derechos_destacados):,} derechos estratégicos a {out_destacados}...")
    with open(out_destacados, "w", encoding="utf-8") as f:
        json.dump(derechos_destacados, f, ensure_ascii=False, indent=2)

    return {
        "total_derechos_cpa": total_scanned,
        "derechos_estrategicos_grafo": len(derechos_destacados),
        "cuencas_procesadas": len(resumen_cuencas_list),
        "caudal_consuntivo_nacional_lps": round(total_consuntivo_nacional_lps, 2),
        "caudal_no_consuntivo_nacional_lps": round(total_no_consuntivo_nacional_lps, 2)
    }


if __name__ == "__main__":
    report = process_cpa_derechos()
    print("\n[OK] Pipeline CPA completado:")
    for k, v in report.items():
        print(f"    - {k}: {v:,}" if isinstance(v, (int, float)) else f"    - {k}: {v}")
