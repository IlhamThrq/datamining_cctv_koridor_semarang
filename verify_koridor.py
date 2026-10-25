"""Verify that all 13 corridor cameras are live before finalizing the collector list.

Fallbacks are tested only when a primary candidate fails.
"""
import json
import time

import cv2

PRIMARY = [
    ("JR01", "JRAKAH", "cd99f288-896a-4e73-9d8c-275ac0008a7d"),
    ("KP01", "COUNTING KRAPYAK", "60690ef5-ec79-4020-ae17-788a9df42566"),
    ("HN01", "HANOMAN", "c83dfda9-1e9e-4b8a-8c83-f7396d7781e4"),
    ("KB01", "KALIBANTENG", "14692ada-0bf1-4da9-bd4f-13a926804958"),
    ("KG01", "KARANGAYU KE TIMUR", "fcd5964e-b58b-48f5-b6f0-3e9af143f5c8"),
    ("IB01", "INDRAPRASTA-IMAM BONJOL", "0b44f5b2-780d-4f86-9ecd-801041b8925a"),
    ("SP01", "SIMPANG LIMA 2", "7af16225-3215-49b7-8966-d649a947960d"),
    ("PH01", "DPU_PAHLAWAN", "c954ee49-2de6-4e7e-be98-8e17c659f9a9"),
    ("SW01", "SRIWIJAYA 01", "8eb25438-c8d3-4c8d-98fd-be74d14df3fa"),
    ("KW01", "KALIWIRU", "cbb3e887-84c4-43c7-9e70-913dc8f460fd"),
    ("BS01", "BUKIT SARI", "4ff40187-00a9-440f-9256-9c0a89af55aa"),
    ("JT01", "FLY OVER JATINGALEH WIDE", "5b09107f-81a6-4e14-b9b7-7712ef5aef7a"),
    ("SR01", "EXIT TOL SRONDOL", "c3814165-b28d-4a32-b33f-007a8e412003"),
]

FALLBACKS = {
    "SW01": ("SW01", "SRIWIJAYA 02", "b23731ab-2aae-4bd0-8b22-2c47d8461f1a"),
    "KG01": ("KG01", "KARANGAYU KE BARAT", "0305a054-bb38-42f9-801b-113385baa0f6"),
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
