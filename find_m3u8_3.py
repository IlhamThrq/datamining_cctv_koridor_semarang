import requests
import re
import urllib3
urllib3.disable_warnings()

headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get('http://lalin.dishub.semarangkota.go.id/live-streaming-cctv-lalin/', headers=headers)
print("Live stream page length:", len(r.text))
m3u8_links = re.findall(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', r.text)
print("m3u8 found:", m3u8_links)

video_srcs = re.findall(r'<source[^\>]+src=["\']([^"\']+)["\']', r.text)
print("Video sources:", video_srcs[:10])

# check iframe or stream urls
iframes = re.findall(r'<iframe[^\>]+src=["\']([^"\']+)["\']', r.text)
print("iframes:", iframes[:10])

# check inline js in pantausemar
r2 = requests.get('https://pantausemar.semarangkota.go.id/', headers=headers, verify=False)
inline_js = re.findall(r'<script>(.*?)</script>', r2.text, re.DOTALL)
print("Inline scripts in pantausemar:", len(inline_js))
for idx, js in enumerate(inline_js):
    if 'hls' in js.lower() or 'm3u8' in js.lower() or 'cctv' in js.lower():
        print(f"Script {idx}:", js[:300])
