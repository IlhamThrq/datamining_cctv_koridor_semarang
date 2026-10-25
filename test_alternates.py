"""Liveness + sample-frame check for swap candidates near the doubted corridor points.

Saves one sample frame per live candidate to .smoke/alternates/ for vantage comparison.
"""
import time
from pathlib import Path

import cv2

CANDIDATES = [
    # (label, uuid, near which corridor point)
    ("SRIWIJAYA_02", "b23731ab-2aae-4bd0-8b22-2c47d8461f1a", "SW01"),
    ("KYAI_SALEH", "ba20c7a2-f499-48c4-af4f-815068f678a0", "IB01"),
    ("JPO_AHMAD_YANI", "5e20c403-7f34-4749-8f56-3863711e0d38", "SP01"),
    ("SIMPANG_TENTREM", "873d1c8c-56d6-4918-906f-514cbbce5ea4", "SP01"),
    ("ARAH_PANDANARAN", "78e494b8-4873-4bfd-96ad-a319358e3f21", "SW01"),
]

OUT = Path(".smoke/alternates")
OUT.mkdir(parents=True, exist_ok=True)


def main():
    for label, uuid, near in CANDIDATES:
        url = f"https://livepantau.semarangkota.go.id/{uuid}/index.m3u8"
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        deadline = time.monotonic() + 12
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
        if frame is None:
            print(f"[DEAD] {label} (pengganti {near})")
            continue
        h, w = frame.shape[:2]
        if w > 1600:
            frame = cv2.resize(frame, (1600, round(h * 1600 / w)), interpolation=cv2.INTER_AREA)
        path = OUT / f"{label}.jpg"
        cv2.imwrite(str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        print(f"[OK]   {label} (pengganti {near}) {w}x{h} -> {path}")


if __name__ == "__main__":
    main()
