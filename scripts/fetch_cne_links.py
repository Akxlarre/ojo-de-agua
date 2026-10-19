import urllib.request
import re
import ssl

ctx = ssl._create_unverified_context()
url = "https://geoportal.cl/geoportal/catalog/34952/Centrales%20hidroel%C3%A9ctricas"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
try:
    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
        html = resp.read().decode("utf-8", "ignore")
        print(f"Page length: {len(html)}")
        links = re.findall(r'href=[\'"]([^\'"]+)[\'"]', html)
        for l in sorted(set(links)):
            if any(k in l.lower() for k in ["download", "zip", "shp", "kml", "arcgis", "cne", "energia"]):
                print("Link:", l)
except Exception as e:
    print("Error:", e)
