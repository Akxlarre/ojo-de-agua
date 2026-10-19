import os
import urllib.request
import ssl
import zipfile
import io

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
}

RAW_DIR = os.path.join(os.getcwd(), 'data', 'dga_raw')
os.makedirs(RAW_DIR, exist_ok=True)

DOWNLOADS = [
    {
        'id': 'camels_attributes',
        'name': 'CAMELS-CL Atributos Hidrológicos y Climáticos (CR2)',
        'url': 'https://store.pangaea.de/Publications/Alvarez-Garreton-etal_2018/1_CAMELScl_attributes.zip',
        'is_zip': True,
        'extract_dir': os.path.join(RAW_DIR, 'camels_cl')
    },
    {
        'id': 'doh_ssr',
        'name': 'DOH MOP - Base Nacional de Sistemas Sanitarios Rurales (SSR / APR)',
        'url': 'https://datos.gob.cl/dataset/9bead9b2-0b9b-4a16-a893-0a736eec6b9a/resource/77ae7ccf-6387-4a4a-9881-0dd2b9ebc0bb/download/base_ssr.xlsx',
        'is_zip': False,
        'out_file': os.path.join(RAW_DIR, 'base_ssr.xlsx')
    },
    {
        'id': 'cooperativas_apr',
        'name': 'Subsecretaría de Economía - Cooperativas de Agua Potable',
        'url': 'https://datos.gob.cl/uploads/recursos/Agua-potable.csv',
        'is_zip': False,
        'out_file': os.path.join(RAW_DIR, 'cooperativas_agua_potable.csv')
    }
]

for item in DOWNLOADS:
    print(f"\nDescargando: {item['name']}...")
    try:
        req = urllib.request.Request(item['url'], headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            data = resp.read()
            print(f" -> Descargados {len(data):,} bytes ({len(data)/(1024*1024):.2f} MB)")
            if item['is_zip']:
                os.makedirs(item['extract_dir'], exist_ok=True)
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    zf.extractall(item['extract_dir'])
                    print(f" -> Extraído en: {item['extract_dir']}")
                    for f in os.listdir(item['extract_dir']):
                        print(f"    * {f}")
            else:
                with open(item['out_file'], 'wb') as f_out:
                    f_out.write(data)
                print(f" -> Guardado en: {item['out_file']}")
    except Exception as e:
        print(f"Error descargando {item['name']}: {e}")
