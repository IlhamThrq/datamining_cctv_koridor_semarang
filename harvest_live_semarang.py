import requests
import json
import re
import cv2
import os
import time
import numpy as np
import pandas as pd
from datetime import datetime
import urllib3
urllib3.disable_warnings()

headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get('https://pantausemar.semarangkota.go.id/', headers=headers, verify=False)
m = re.search(r'var cctvs\s*=\s*(\[.*?\]);', r.text)
if not m:
    print("Could not find cctvs in Pantau Semar")
    exit(1)

data = json.loads(m.group(1))
all_streams = []
for item in data:
    for l in item.get('links', []):
        url = l.get('url', '')
        if url and 'm3u8' in url:
            all_streams.append({
                'name': l.get('name', 'CCTV'),
                'url': url,
                'lat': item.get('lat'),
                'lng': item.get('lng')
            })

print(f"Total CCTV stream URLs found in Pantau Semar: {len(all_streams)}")

# Select diverse top intersections
selected_names = [
    'SIMPANG LIMA', 'TUGUMUDA', 'KALIBANTENG', 'SIMPANG PARAGON', 'BANGKONG',
    'KARIADI', 'THAMRIN', 'KRAPYAK', 'MILO', 'KALIWIRU'
]

targets = []
for name_keyword in selected_names:
    for s in all_streams:
        if name_keyword.lower() in s['name'].lower():
            targets.append(s)
            break

print(f"Selected {len(targets)} primary intersections for capture:")
for t in targets:
    print(f" - {t['name']}: {t['url'][:55]}...")
