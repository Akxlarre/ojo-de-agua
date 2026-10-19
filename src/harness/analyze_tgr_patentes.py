import os
import sys
import pandas as pd
import json

# Ensure utf-8 stdout
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

csv_path = os.path.join(os.getcwd(), "data", "dga_raw", "tgr_patentes_aguas_2025.csv")
print(f"Cargando dataset TGR desde {csv_path}...")

df = pd.read_csv(csv_path, encoding='latin1', low_memory=False)
df.columns = [c.strip().upper() for c in df.columns]

# Ensure numeric conversions
df['MONTO'] = pd.to_numeric(df['MONTO'], errors='coerce').fillna(0)
df['SALDO'] = pd.to_numeric(df['SALDO'], errors='coerce').fillna(0)
df['PAGADO'] = pd.to_numeric(df['PAGADO'], errors='coerce').fillna(0)
df['UTM'] = pd.to_numeric(df['UTM'], errors='coerce').fillna(0)

# Summary statistics
total_deuda_clp = float(df['SALDO'].sum())
total_monto_clp = float(df['MONTO'].sum())
total_pagado_clp = float(df['PAGADO'].sum())
total_utm = float(df['UTM'].sum())
total_registros = int(len(df))
total_ruts_unicos = int(df['RUT_ROL'].nunique())

print("\n" + "=" * 60)
print("   RESUMEN FINANCIERO Y LEGAL - PATENTES POR NO USO DE AGUAS")
print("=" * 60)
print(f"Total Registros Liquidados: {total_registros:,}")
print(f"Titulares Únicos (RUTs): {total_ruts_unicos:,}")
print(f"Monto Total Emitido: ${total_monto_clp:,.0f} CLP")
print(f"Monto Pagado: ${total_pagado_clp:,.0f} CLP ({(total_pagado_clp/total_monto_clp*100) if total_monto_clp else 0:.1f}%)")
print(f"Deuda Pendiente (Saldo No Pagado): ${total_deuda_clp:,.0f} CLP")
print(f"Total UTM Liquidadas: {total_utm:,.1f} UTM")

# Top Regiones
top_reg = df.groupby('TESORERIA_REGIONAL').agg(
    registros=('RUT_ROL', 'count'),
    deuda_clp=('SALDO', 'sum'),
    utm=('UTM', 'sum')
).sort_values(by='deuda_clp', ascending=False)

print("\nTop 10 Regiones con Mayor Deuda por No Uso de Aguas:")
for reg, row in top_reg.head(10).iterrows():
    print(f" * {reg}: ${row['deuda_clp']:,.0f} CLP ({row['utm']:,.1f} UTM, {row['registros']:,} patentes)")

# Top Comunas
top_com = df.groupby('COMUNA').agg(
    region=('TESORERIA_REGIONAL', 'first'),
    registros=('RUT_ROL', 'count'),
    deuda_clp=('SALDO', 'sum'),
    utm=('UTM', 'sum')
).sort_values(by='deuda_clp', ascending=False)

print("\nTop 10 Comunas Críticas con Mayor Especulación Hídrica:")
for com, row in top_com.head(10).iterrows():
    print(f" * {com} ({row['region']}): ${row['deuda_clp']:,.0f} CLP ({row['registros']:,} patentes)")

# Top 15 Mayores Deudores por RUT
top_rut = df.groupby(['RUT_ROL', 'TIPO_PERSONA']).agg(
    cantidad_derechos=('FORM_FOLIO', 'count'),
    saldo_clp=('SALDO', 'sum'),
    utm=('UTM', 'sum'),
    comuna_principal=('COMUNA', 'first'),
    region_principal=('TESORERIA_REGIONAL', 'first'),
    cbr=('OFICINA_CBR', 'first')
).sort_values(by='saldo_clp', ascending=False).reset_index()

print("\nTop 10 Mayores Tenedores de Derechos en No Uso (RUT):")
for idx, r in top_rut.head(10).iterrows():
    print(f" {idx+1}. RUT {r['RUT_ROL']} [{r['TIPO_PERSONA']}]: ${r['saldo_clp']:,.0f} CLP ({r['utm']:,.1f} UTM) - {r['cantidad_derechos']} derechos en {r['comuna_principal']} (CBR {r['cbr']})")

# Save structured summary to data/
summary_json = {
    "total_registros_patentes": total_registros,
    "total_titulares_unicos": total_ruts_unicos,
    "monto_total_emitido_clp": total_monto_clp,
    "monto_pagado_clp": total_pagado_clp,
    "deuda_pendiente_clp": total_deuda_clp,
    "total_utm_liquidadas": total_utm,
    "desglose_por_tipo": {
        "juridica": {
            "registros": int(df[df['TIPO_PERSONA'] == 'JURIDICA']['RUT_ROL'].count()),
            "deuda_clp": float(df[df['TIPO_PERSONA'] == 'JURIDICA']['SALDO'].sum()),
            "utm": float(df[df['TIPO_PERSONA'] == 'JURIDICA']['UTM'].sum())
        },
        "natural": {
            "registros": int(df[df['TIPO_PERSONA'] == 'NATURAL']['RUT_ROL'].count()),
            "deuda_clp": float(df[df['TIPO_PERSONA'] == 'NATURAL']['SALDO'].sum()),
            "utm": float(df[df['TIPO_PERSONA'] == 'NATURAL']['UTM'].sum())
        }
    },
    "ranking_regiones": [
        {
            "region": reg,
            "deuda_clp": float(row['deuda_clp']),
            "utm": float(row['utm']),
            "patentes_acumuladas": int(row['registros'])
        }
        for reg, row in top_reg.iterrows()
    ],
    "ranking_comunas_top_25": [
        {
            "comuna": com,
            "region": row['region'],
            "deuda_clp": float(row['deuda_clp']),
            "utm": float(row['utm']),
            "patentes_acumuladas": int(row['registros'])
        }
        for com, row in top_com.head(25).iterrows()
    ],
    "ranking_titulares_top_50": [
        {
            "ranking": idx + 1,
            "rut": str(row['RUT_ROL']),
            "tipo_persona": row['TIPO_PERSONA'],
            "saldo_clp": float(row['saldo_clp']),
            "utm": float(row['utm']),
            "cantidad_derechos": int(row['cantidad_derechos']),
            "comuna_principal": str(row['comuna_principal']),
            "region_principal": str(row['region_principal']),
            "oficina_cbr": str(row['cbr'])
        }
        for idx, row in top_rut.head(50).iterrows()
    ]
}

out_summary = os.path.join(os.getcwd(), "data", "patentes_no_uso_chile.json")
with open(out_summary, "w", encoding="utf-8") as f:
    json.dump(summary_json, f, indent=2, ensure_ascii=False)

print(f"\nResumen y ranking de fiscalización guardado exitosamente en:\n -> {out_summary}")
