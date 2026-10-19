import urllib.request
import re
import ssl

ctx = ssl._create_unverified_context()
url = 'https://geoportal.cl/geoportal/catalog/35179/Plantas%20de%20tratamiento%20de%20aguas%20servidas%20%28PTAS%29,%20Descargas%20de%20PTAS,%20Territorio%20Operacional%20y%20Grifos.'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
try:
    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
        html = resp.read().decode('utf-8', 'ignore')
        print(f"Page length: {len(html)}")
        links = re.findall(r'href=[\'"]([^\'"]+)[\'"]', html)
        for l in sorted(set(links)):
            if any(k in l.lower() for k in ['siss', 'arcgis', 'wfs', 'wms', 'zip', 'shp', 'geojson', 'download', 'feature', 'geoserver']):
                print("Found link:", l)
except Exception as e:
    print("Error:", e)
