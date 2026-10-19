import os
import shapefile
import pandas as pd

base = os.path.join(os.getcwd(), 'data', 'dga_raw')

print("=== 1. SHAC / ACUÍFEROS ===")
shac_path = os.path.join(base, 'shac', 'Acuiferos_SHAC', 'INV_ACUIFEROS_SHAC.shp')
with shapefile.Reader(shac_path, encoding='latin1') as sf:
    print(f"Total SHAC shapes: {len(sf)}")
    fields = [f[0] for f in sf.fields[1:]]
    print(f"Fields: {fields}")
    for i in range(min(5, len(sf))):
        rec = sf.record(i).as_dict()
        print(f" Record {i+1}: COD_ACUIF={rec.get('COD_ACUIF')}, NOMBRE={rec.get('NOMBRE')}, SHAC={rec.get('SHAC')}, COD_CUEN={rec.get('COD_CUEN')}, NOM_CUEN={rec.get('NOM_CUEN')}, ESTADO={rec.get('ESTADO')}")

print("\n=== 2. RED HIDROMÉTRICA NACIONAL (BNA) ===")
bna_path = os.path.join(base, 'red_bna', 'Red_Hidrometrica_Nacional', 'Red_Hidrometrica_Nacional.shp')
with shapefile.Reader(bna_path, encoding='latin1') as sf:
    print(f"Total BNA stations: {len(sf)}")
    types = set()
    cuencas = set()
    for rec in sf.records():
        d = rec.as_dict()
        t = d.get('TIPO_EST_1') or d.get('TIPO_ESTAC')
        if t:
            types.add(str(t).strip())
        c = d.get('NOM_CUEN')
        if c:
            cuencas.add(str(c).strip())
    print(f"Types of stations ({len(types)}): {sorted(list(types))[:10]}")
    print(f"Total cuencas with BNA stations: {len(cuencas)}")

print("\n=== 3. DECRETOS ESCASEZ EXCEL ===")
esc_path = os.path.join(base, 'decretos_escasez_historico.xls')
df_esc = pd.read_excel(esc_path)
print("Decretos Escasez Shape:", df_esc.shape)
print("Decretos Columns:", df_esc.columns.tolist())
print(df_esc.head(5))

print("\n=== 4. DECLARACIÓN AGOTAMIENTO EXCEL ===")
ago_path = os.path.join(base, 'declaracion_agotamiento.xls')
df_ago = pd.read_excel(ago_path)
print("Agotamiento Shape:", df_ago.shape)
print("Agotamiento Columns:", df_ago.columns.tolist())
print(df_ago.head(5))

print("\n=== 5. ZONAS PROHIBICIÓN EXCEL ===")
zp_path = os.path.join(base, 'zonas_prohibicion.xlsx')
df_zp = pd.read_excel(zp_path, skiprows=3)
print("Zonas Prohibición Shape:", df_zp.shape)
print("Zonas Prohibición Columns:", df_zp.columns.tolist())
print(df_zp.head(5))
