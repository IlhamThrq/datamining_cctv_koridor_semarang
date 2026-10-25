import requests
import re
import urllib3
urllib3.disable_warnings()

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

print("--- 1. Testing lalin.dishub.semarangkota.go.id ---")
try:
    r = requests.get('http://lalin.dishub.semarangkota.go.id', headers=headers, timeout=8)
    print("Lalin status:", r.status_code)
    m3u8_links = re.findall(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', r.text)
    print("M3U8 in lalin:", m3u8_links[:5])
except Exception as e:
    print("Error lalin:", e)

print("\n--- 2. Testing pantausemar.semarangkota.go.id ---")
try:
    r = requests.get('https://pantausemar.semarangkota.go.id/', headers=headers, timeout=8, verify=False)
    print("Pantausemar status:", r.status_code)
    m3u8_links = re.findall(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', r.text)
    print("Direct m3u8:", m3u8_links[:5])
    # check js files
    scripts = re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', r.text)
    print("Scripts found:", len(scripts))
    for s in scripts:
        if 'app' in s or 'cctv' in s or 'main' in s:
            print("Target script:", s)
except Exception as e:
    print("Error pantausemar:", e)
