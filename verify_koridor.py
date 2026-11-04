"""Verify that all 13 corridor cameras are live before finalizing the collector list.

Fallbacks are tested only when a primary candidate fails.
"""
import json
import time

import cv2

PRIMARY = [
    ("JR01", "JRAKAH", "c095f541-afc8-4125-8e2a-50bdb824ec81"),
    ("KP01", "COUNTING KRAPYAK", "3ef0e69f-129a-40ef-9778-17c6c6d40158"),
    ("HN01", "HANOMAN", "8dcb30a0-3c68-4514-9ccb-76a41e1fc387"),
    ("KB01", "KALIBANTENG", "a4089997-8fae-442a-91a2-2922f07ded05"),
    ("KG01", "KARANGAYU KE TIMUR", "899f25a5-211b-43aa-a70d-7660d0e60918"),
    ("IB01", "INDRAPRASTA-IMAM BONJOL", "aa7948d5-026f-4501-9755-7467fc35300f"),
    ("SP01", "JPO AHMAD YANI", "af82809a-39e8-487d-9fb4-ce460b82ef78"),
    ("PH01", "DPU_PAHLAWAN", "19e497ac-604b-462f-a0c3-1496fdd54f23"),
    ("SW01", "SRIWIJAYA 02", "87a39500-0a2a-41ec-bbbe-1bc6d3160de5"),
    ("KW01", "KALIWIRU", "fd400d25-76d9-4006-8cd3-47b9b5f52755"),
    ("BS01", "BUKIT SARI", "b957cfea-831c-420d-a09c-2d388ff7b7ce"),
    ("JT01", "FLY OVER JATINGALEH WIDE", "1f29fa3e-907f-4ff6-88c1-fb97d8a3df83"),
    ("SR01", "EXIT TOL SRONDOL", "c275ab86-3f2b-4e9c-b2ce-6e7e6b8f49ed"),
]

FALLBACKS = {
    "HN01": ("HN01", "RUAS KERAPYAK", "892fa5db-3bea-4412-876f-5e606a646b76"),
    "SW01": ("SW01", "SRIWIJAYA 01", "19dff7be-9f14-4103-a34c-fecd4d7b18ae"),
    "KG01": ("KG01", "KARANGAYU KE BARAT", "0366cbe7-d756-4f5f-b4aa-ef3ecf89d967"),
}


def url_for(uuid: str) -> str:
    return f"https://livepantau.semarangkota.go.id/{uuid}/index.m3u8"


def probe(label: str, uuid: str, timeout: float = 12.0):
    cap = cv2.VideoCapture(url_for(uuid), cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    deadline = time.monotonic() + timeout
    frame = None
    try:
        while time.monotonic() < deadline:
            ok, f = cap.read()
            if ok and f is not None:
                frame = f
                break
            time.sleep(0.2)
    finally:
        cap.release()
    if frame is not None:
        h, w = frame.shape[:2]
        print(f"  [OK]   {label:<32} {w}x{h}  {uuid}", flush=True)
        return {"label": label, "uuid": uuid, "w": w, "h": h}
    print(f"  [DEAD] {label:<32} {uuid}", flush=True)
    return None


def main():
    results = {}
    for cam_id, name, uuid in PRIMARY:
        print(f"Testing {cam_id} {name}...", flush=True)
        got = probe(f"{cam_id} {name}", uuid)
        if got is None and cam_id in FALLBACKS:
            fb_id, fb_name, fb_uuid = FALLBACKS[cam_id]
            print(f"  -> trying fallback {fb_name}", flush=True)
            got = probe(f"{fb_id} {fb_name}", fb_uuid)
        results[cam_id] = got

    alive = {k: v for k, v in results.items() if v is not None}
    print(f"\nTotal live: {len(alive)}/{len(PRIMARY)}", flush=True)
    with open("verify_koridor_result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    if len(alive) < len(PRIMARY):
        missing = [k for k, v in results.items() if v is None]
        print(f"Still dead (need manual replacement): {', '.join(missing)}", flush=True)


if __name__ == "__main__":
    main()
