import requests
import re
import urllib3
urllib3.disable_warnings()

r = requests.get('https://binamarga.pu.go.id/contents/cctv_tol/?id_ruas=semarang-abc', timeout=10, verify=False)
urls = re.findall(r'https?://[^\s"\'<>]+\.(?:jpg|m3u8)', r.text)
print("Found URLs:", len(urls))
for u in set(urls)[:10]:
    print(u)
