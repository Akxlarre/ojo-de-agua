import urllib.request
import ssl

ctx = ssl._create_unverified_context()
url = "https://www.geoportal.cl/geoportal/catalog/download/3087c4d0-711f-3781-a41c-d849f2b51966"
req = urllib.request.Request(url, headers={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
})
try:
    with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:
        print("Status:", resp.status)
        print("Headers:", dict(resp.headers))
        data = resp.read()
        print("Downloaded:", len(data), "bytes")
        with open("data/dga_raw/siss_ptas_geoportal.zip", "wb") as f:
            f.write(data)
        print("Saved to data/dga_raw/siss_ptas_geoportal.zip")
except Exception as e:
    print("Error:", e)
