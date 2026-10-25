import requests
import re
import json
import urllib3
urllib3.disable_warnings()

headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get('https://pantausemar.semarangkota.go.id/', headers=headers, verify=False)

# Look for player logic or modal logic
matches = re.findall(r'function\s+play[a-zA-Z0-9_]*\s*\([^\)]*\)\s*\{[^}]+\}', r.text)
for m in matches[:5]:
    print("Player func:", m)

# Look for cctvs variable definition
m_cctvs = re.search(r'var cctvs\s*=\s*(\[.*?\]);', r.text)
if m_cctvs:
    raw_json = m_cctvs.group(1)
    data = json.loads(raw_json)
    print("Total CCTV cameras in Pantau Semar:", len(data))
    for item in data:
        name = item.get('owner_name', '') or ''
        if any(k in name.lower() for k in ['simpang', 'tugu', 'kali', 'peterongan']):
            print("Found:", item.get('cctv_id'), name, item.get('links'))
