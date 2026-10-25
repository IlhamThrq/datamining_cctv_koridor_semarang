import requests
import re
import urllib3
urllib3.disable_warnings()

headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get('https://pantausemar.semarangkota.go.id/', headers=headers, verify=False)
scripts = re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', r.text)
for s in scripts:
    print(s)

print("\n--- Inspecting lalin.dishub HTML content ---")
r2 = requests.get('http://lalin.dishub.semarangkota.go.id', headers=headers)
print("Lalin length:", len(r2.text))
streams = re.findall(r'https?://[^\s"\'<>]+', r2.text)
for st in streams:
    if any(k in st.lower() for k in ['stream', 'cctv', 'video', 'live', 'rtsp']):
        print(st)
