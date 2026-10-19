import os
import urllib.request
import ssl
import zipfile
import io
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Referer': 'https://dga.mop.gob.cl/search/'
}

TARGET_DIR = os.path.join(os.getcwd(), 'data', 'dga_raw')
os.makedirs(TARGET_DIR, exist_ok=True)

DOWNLOADS = [
    {
        'id': 'shac',
        'name': 'Acuíferos y SHAC Nacional',
        'url': 'https://dga.mop.gob.cl/uploads/sites/13/2024/07/Acuiferos_SHAC-2.zip',
        'is_zip': True
    },
    {
        'id': 'red_bna',
        'name': 'Red Hidrométrica Nacional (BNA)',
        'url': 'https://dga.mop.gob.cl/uploads/sites/13/2024/07/Red_Hidrometrica_Nacional-1.zip',
        'is_zip': True
    },
    {
        'id': 'decretos_escasez',
        'name': 'Planilla Histórica de Decretos de Escasez (2008-2026)',
        'url': 'https://dga.mop.gob.cl/uploads/sites/13/2024/07/Decretos_zonas_escasez_historico_04-09-2026.xls',
        'is_zip': False,
        'filename': 'decretos_escasez_historico.xls'
    },
    {
        'id': 'agotamiento',
        'name': 'Declaraciones de Agotamiento Superficial',
        'url': 'https://dga.mop.gob.cl/uploads/sites/13/2024/11/declaracion_agotamiento.xls',
        'is_zip': False,
        'filename': 'declaracion_agotamiento.xls'
    },
    {
        'id': 'zonas_prohibicion',
        'name': 'Zonas de Prohibición Subterránea',
        'url': 'https://dga.mop.gob.cl/uploads/sites/13/2024/07/zonas_prohibicion-16-03-2026.xlsx',
        'is_zip': False,
        'filename': 'zonas_prohibicion.xlsx'
    },
    {
        'id': 'embalses',
        'name': 'Inventario de Embalses DGA',
        'url': 'https://dga.mop.gob.cl/uploads/sites/13/2024/07/Inventario_de_Embalses.zip',
        'is_zip': True
    }
]

print(f"Target directory: {TARGET_DIR}")

for item in DOWNLOADS:
    print(f"\nProcessing: {item['name']}...")
    try:
        req = urllib.request.Request(item['url'], headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            data = resp.read()
            print(f" -> Downloaded {len(data)} bytes.")
            if item.get('is_zip'):
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    extract_path = os.path.join(TARGET_DIR, item['id'])
                    os.makedirs(extract_path, exist_ok=True)
                    zf.extractall(extract_path)
                    print(f" -> Extracted to: {extract_path}")
                    for f in os.listdir(extract_path):
                        print(f"    - {f}")
            else:
                out_path = os.path.join(TARGET_DIR, item['filename'])
                with open(out_path, 'wb') as f_out:
                    f_out.write(data)
                print(f" -> Saved to: {out_path}")
    except Exception as e:
        print(f" -> Error downloading {item['name']}: {e}")
