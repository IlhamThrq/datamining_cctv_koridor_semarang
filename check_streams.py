import requests
import json
import re
import urllib3
import cv2

urllib3.disable_warnings()

headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get('https://pantausemar.semarangkota.go.id/', headers=headers, verify=False)
m = re.search(r'var cctvs\s*=\s*(\[.*?\]);', r.text)

if not m:
    print("Could not find cctvs array.")
    exit(1)

data = json.loads(m.group(1))
print(f"Total CCTV entries: {len(data)}")

all_streams = []
for item in data:
    cctv_id = item.get('cctv_id')
    loc_name = item.get('owner_name') or ''
    lat = item.get('lat')
    lng = item.get('lng')
    for l in item.get('links', []):
        url = l.get('url', '')
        if url and 'm3u8' in url:
            all_streams.append({
                'cctv_id': str(cctv_id),
                'link_id': str(l.get('id', '')),
                'name': l.get('name', loc_name),
                'url': url,
                'lat': lat,
                'lng': lng
            })

print(f"Found {len(all_streams)} m3u8 streams.")
# Save to json for quick reference
with open('pantausemar_streams.json', 'w', encoding='utf-8') as f:
    json.dump(all_streams, f, indent=2)

# Test the first 20 streams with cv2 to see which are responsive
print("\nTesting streams for frame capture...")
active_streams = []
for s in all_streams:
    cap = cv2.VideoCapture(s['url'], cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    ok, frame = cap.read()
    cap.release()
    status = "OK" if ok else "FAILED"
    print(f"[{status}] {s['name']} -> {s['url'][:60]}")
    if ok:
        active_streams.append(s)
        if len(active_streams) >= 12:
            break

print(f"\nActive verified streams count: {len(active_streams)}")
with open('verified_streams.json', 'w', encoding='utf-8') as f:
    json.dump(active_streams, f, indent=2)
