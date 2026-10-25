"""Multi-camera real-time ATCS frame collector for Kota Semarang.

Captures timestamped frames concurrently from 12 verified public ATCS CCTV streams.
No fabricated vehicle counts, weather, or speed estimates are written.
Image quality metrics (luminance, blur/laplacian, dHash, SHA-256) are computed from real frames.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import signal
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
JAKARTA = ZoneInfo("Asia/Jakarta")
STOP = False

FIELDS = [
    "frame_id",
    "capture_timestamp",
    "source_url",
    "camera_id",
    "camera_name",
    "capture_status",
    "frame_path",
    "resolution_w",
    "resolution_h",
    "mean_luminance",
    "laplacian_variance",
    "dhash_hex",
    "sha256",
    "is_duplicate_of_previous",
    "vehicle_count",
    "weather_condition",
    "speed_estimate_kmh",
]

DEFAULT_CAMERAS = [
    {
        "camera_id": "SP01",
        "name": "SIMPANG LIMA 2",
        "url": "https://livepantau.semarangkota.go.id/7af16225-3215-49b7-8966-d649a947960d/index.m3u8",
        "lat": -6.9897019,
        "lng": 110.4239394,
        "zone": "Pusat / CBD"
    },
    {
        "camera_id": "TM01",
        "name": "TUGUMUDA 2 WIDE",
        "url": "https://livepantau.semarangkota.go.id/26306fea-44d0-4fa7-a82d-c153e86deaa2/index.m3u8",
        "lat": -6.9840857,
        "lng": 110.4095746,
        "zone": "Pusat / Landmark"
    },
    {
        "camera_id": "TH01",
        "name": "SIMPANG THAMRIN",
        "url": "https://livepantau.semarangkota.go.id/3278760a-a203-4eb4-a331-3519eeb6bd1a/index.m3u8",
        "lat": -6.9855331,
        "lng": 110.4176166,
        "zone": "Pusat / Koridor Bisnis"
    },
    {
        "camera_id": "BK02",
        "name": "BALAIKOTA",
        "url": "https://livepantau.semarangkota.go.id/bfcb0bac-048f-4b4f-a607-83267af978dc/index.m3u8",
        "lat": -6.9818029,
        "lng": 110.4120375,
        "zone": "Pusat / Pemerintahan"
    },
    {
        "camera_id": "KR01",
        "name": "KARIADI",
        "url": "https://livepantau.semarangkota.go.id/30993efa-38bc-42f7-a74e-7044fe42e3a9/index.m3u8",
        "lat": -6.9944564,
        "lng": 110.4067973,
        "zone": "Pusat-Selatan / RS"
    },
    {
        "camera_id": "BK01",
        "name": "BANGKONG",
        "url": "https://livepantau.semarangkota.go.id/b8013256-1adc-4d5f-aed6-b28ed7d0b52e/index.m3u8",
        "lat": -6.9943447,
        "lng": 110.4319730,
        "zone": "Timur / Simpang Arteri"
    },
    {
        "camera_id": "ML01",
        "name": "MILO",
        "url": "https://livepantau.semarangkota.go.id/1e056193-d64c-4e53-84a1-41a55d373ad0/index.m3u8",
        "lat": -6.9950314,
        "lng": 110.4338415,
        "zone": "Timur / Stadion-Mataram"
    },
    {
        "camera_id": "FW01",
        "name": "FATMAWATI",
        "url": "https://livepantau.semarangkota.go.id/5d13ca45-d96a-43b0-af69-6b01c5168305/index.m3u8",
        "lat": -7.0111193,
        "lng": 110.4727828,
        "zone": "Timur / Pedurungan"
    },
    {
        "camera_id": "KW01",
        "name": "KALIWIRU",
        "url": "https://livepantau.semarangkota.go.id/cbb3e887-84c4-43c7-9e70-913dc8f460fd/index.m3u8",
        "lat": -7.0234964,
        "lng": 110.4203931,
        "zone": "Selatan / Akses Tol-Gombel"
    },
    {
        "camera_id": "KB01",
        "name": "KALIBANTENG",
        "url": "https://livepantau.semarangkota.go.id/14692ada-0bf1-4da9-bd4f-13a926804958/index.m3u8",
        "lat": -6.9845739,
        "lng": 110.3835144,
        "zone": "Barat / Bandara-Flyover"
    },
    {
        "camera_id": "HN01",
        "name": "HANOMAN",
        "url": "https://livepantau.semarangkota.go.id/c83dfda9-1e9e-4b8a-8c83-f7396d7781e4/index.m3u8",
        "lat": -6.9866287,
        "lng": 110.3750852,
        "zone": "Barat / Arteri Siliwangi"
    },
    {
        "camera_id": "JR01",
        "name": "JRAKAH",
        "url": "https://livepantau.semarangkota.go.id/cd99f288-896a-4e73-9d8c-275ac0008a7d/index.m3u8",
        "lat": -6.9866272,
        "lng": 110.3605996,
        "zone": "Barat / Pintu Masuk Kendal"
    },
]


def stop_capture(_signum, _frame):
    global STOP
    print("\n[STOP] Signal received. Shutting down capture safely...", flush=True)
    STOP = True


def image_metrics(frame: np.ndarray) -> tuple[float, float, str, str]:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    reduced = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
    bits = reduced[:, 1:] > reduced[:, :-1]
    dhash = sum(int(value) << index for index, value in enumerate(bits.ravel()))
    return (
        round(float(gray.mean()), 3),
        round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 3),
        f"{dhash:016x}",
        hashlib.sha256(frame.tobytes()).hexdigest(),
    )


def capture_single_camera(cam: dict, timeout: float = 8.0) -> tuple[dict, np.ndarray | None]:
    """Capture a single frame from one camera stream with timeout."""
    cap = cv2.VideoCapture(cam["url"], cv2.CAP_FFMPEG)
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

    return cam, frame


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=float, default=120.0, help="Seconds between capture cycles (default: 120)")
    parser.add_argument("--duration", type=float, default=0, help="Stop after N seconds; 0 means continuous run")
    parser.add_argument("--timeout", type=float, default=8.0, help="Per-camera stream read timeout in seconds")
    parser.add_argument("--output", type=Path, default=ROOT / "data")
    parser.add_argument("--threads", type=int, default=6, help="Concurrent capture threads")
    args = parser.parse_args()

    frames_dir = args.output / "raw_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output / "raw_cctv_metadata.csv"
    file_exists = csv_path.exists() and csv_path.stat().st_size > 0

    # Save registry
    registry_path = args.output / "camera_registry.json"
    with registry_path.open("w", encoding="utf-8") as f:
        json.dump(DEFAULT_CAMERAS, f, indent=2)

    csv_file = csv_path.open("a", newline="", encoding="utf-8")
    writer = csv.DictWriter(csv_file, fieldnames=FIELDS)
    if not file_exists:
        writer.writeheader()
        csv_file.flush()

    signal.signal(signal.SIGINT, stop_capture)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, stop_capture)

    # Track frame indices per camera
    frame_indices: dict[str, int] = {cam["camera_id"]: 0 for cam in DEFAULT_CAMERAS}
    previous_hashes: dict[str, str] = {}

    # Initialize frame count from existing CSV if present
    if file_exists:
        with csv_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cid = row.get("camera_id")
                if cid in frame_indices:
                    frame_indices[cid] += 1
                if cid and row.get("sha256"):
                    previous_hashes[cid] = row["sha256"]

    print(f"============================================================")
    print(f" ATCS Kota Semarang - Live Multi-Camera Frame Collector")
    print(f" Target Cameras : {len(DEFAULT_CAMERAS)} intersections")
    print(f" Cycle Interval : {args.interval:.1f}s")
    print(f" Parallelism    : {args.threads} worker threads")
    print(f" Output CSV     : {csv_path}")
    print(f" Frames Dir     : {frames_dir}")
    print(f" Started At     : {datetime.now(JAKARTA).strftime('%Y-%m-%d %H:%M:%S WIB')}")
    print(f" Press Ctrl+C at any time to stop safely.")
    print(f"============================================================", flush=True)

    started = time.monotonic()
    cycle = 0

    try:
        while not STOP and (args.duration == 0 or time.monotonic() - started < args.duration):
            cycle_start = time.monotonic()
            cycle += 1
            now_dt = datetime.now(JAKARTA)
            timestamp_str = now_dt.isoformat(timespec="seconds")
            time_display = now_dt.strftime("%H:%M:%S")

            print(f"\n--- [Cycle #{cycle:03d} | {time_display} WIB] Polling {len(DEFAULT_CAMERAS)} cameras ---", flush=True)

            results: list[dict] = []
            with ThreadPoolExecutor(max_workers=args.threads) as executor:
                futures = {
                    executor.submit(capture_single_camera, cam, args.timeout): cam
                    for cam in DEFAULT_CAMERAS
                }
                for fut in as_completed(futures):
                    cam, frame = fut.result()
                    cid = cam["camera_id"]
                    cname = cam["name"]
                    frame_indices[cid] += 1
                    fid = f"{cid}_{now_dt:%Y%m%dT%H%M%S}_{frame_indices[cid]:07d}"

                    row = {
                        "frame_id": fid,
                        "capture_timestamp": timestamp_str,
                        "source_url": cam["url"],
                        "camera_id": cid,
                        "camera_name": cname,
                        "capture_status": "stream_error",
                        "frame_path": "",
                        "resolution_w": "",
                        "resolution_h": "",
                        "mean_luminance": "",
                        "laplacian_variance": "",
                        "dhash_hex": "",
                        "sha256": "",
                        "is_duplicate_of_previous": "",
                        "vehicle_count": "",
                        "weather_condition": "",
                        "speed_estimate_kmh": "",
                    }

                    if frame is not None:
                        h, w = frame.shape[:2]
                        mean_lum, lap_var, dhash, sha = image_metrics(frame)
                        is_dup = (previous_hashes.get(cid) == sha)
                        previous_hashes[cid] = sha

                        frame_fname = f"{fid}.jpg"
                        frame_target = frames_dir / frame_fname
                        if cv2.imwrite(str(frame_target), frame):
                            row.update({
                                "capture_status": "captured",
                                "frame_path": str(frame_target.relative_to(args.output.parent)),
                                "resolution_w": w,
                                "resolution_h": h,
                                "mean_luminance": mean_lum,
                                "laplacian_variance": lap_var,
                                "dhash_hex": dhash,
                                "sha256": sha,
                                "is_duplicate_of_previous": str(is_dup).lower(),
                            })
                            dup_flag = " [DUPLICATE]" if is_dup else ""
                            print(f"  [OK] {cid:<4} {cname:<18} ({w}x{h}) | Lum={mean_lum:5.1f} | BlurVar={lap_var:6.1f}{dup_flag}", flush=True)
                        else:
                            row["capture_status"] = "write_error"
                            print(f"  [ERR] {cid:<4} {cname:<18} Disk write failed!", flush=True)
                    else:
                        print(f"  [OFFLINE] {cid:<4} {cname:<18} Stream timed out/unavailable", flush=True)

                    results.append(row)

            # Write batch to CSV
            for r in results:
                writer.writerow(r)
            csv_file.flush()

            ok_count = sum(1 for r in results if r["capture_status"] == "captured")
            elapsed = time.monotonic() - cycle_start
            print(f"Cycle completed in {elapsed:.1f}s: {ok_count}/{len(DEFAULT_CAMERAS)} frames captured successfully.", flush=True)

            # Sleep until next cycle
            sleep_time = args.interval - elapsed
            if sleep_time > 0 and not STOP:
                time.sleep(sleep_time)

    finally:
        csv_file.close()
        print(f"\n[DONE] Collector session ended cleanly. Frames and metadata saved in {args.output}.", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
