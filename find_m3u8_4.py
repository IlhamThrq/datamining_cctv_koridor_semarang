import requests
import re
import json
import urllib3
urllib3.disable_warnings()

headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get('https://pantausemar.semarangkota.go.id/', headers=headers, verify=False)
inline_js = re.findall(r'<script>(.*?)</script>', r.text, re.DOTALL)

for js in inline_js:
    if 'geojsonFeature' in js:
        # find stream or cctv info
        print("Geojson script length:", len(js))
        lines = [l for l in js.split('\n') if any(k in l.lower() for k in ['simpang', 'tugu', 'm3u8', 'stream', 'hls'])]
        print("Matching lines found:", len(lines))
        for l in lines[:15]:
            print(l[:180])
