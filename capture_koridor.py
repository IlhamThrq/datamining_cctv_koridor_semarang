"""Corridor frame collector for the Kaliwungu-Tembalang commuter route, Kota Semarang.

Captures timestamped frames concurrently from 13 verified public ATCS CCTV streams
arranged along the commute corridor (route_order 1-13). Fixed-view cameras only;
PTZ/360 cameras are excluded by design so time-series comparisons stay valid.
Frames wider than MAX_WIDTH px are downscaled and stored as JPEG quality 80 to
keep the weekly dataset around 1.5-2 GB. No vehicle counts, weather, or speed
values are synthesized; those columns stay empty until real inference is run.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import signal
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
MAX_WIDTH = 1600
JPEG_QUALITY = 80

FIELDS = [
    "frame_id",
    "capture_timestamp",
    "source_url",
    "camera_id",
    "camera_name",
    "route_order",
    "route",
    "zone",
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

# Ordered along the commute: Kaliwungu (Kendal) -> pantura -> CBD -> Tembalang.
# "arterial" = primary surface route, "tol" = toll alternative (Jatingaleh-Srondol).
CAMERAS = [
    {
        "camera_id": "JR01",
        "name": "JRAKAH",
        "url": "https://livepantau.semarangkota.go.id/cd99f288-896a-4e73-9d8c-275ac0008a7d/index.m3u8",
        "lat": -6.9866272,
        "lng": 110.3605996,
        "route_order": 1,
        "route": "arterial",
        "zone": "Barat / Gerbang Kendal",
    },
    {
        "camera_id": "KP01",
        "name": "COUNTING KRAPYAK",
        "url": "https://livepantau.semarangkota.go.id/60690ef5-ec79-4020-ae17-788a9df42566/index.m3u8",
        "lat": -6.9877794,
        "lng": 110.3682006,
        "route_order": 2,
        "route": "arterial",
        "zone": "Barat / Gerbang Tol Krapyak",
    },
    {
        "camera_id": "HN01",
        "name": "HANOMAN",
        "url": "https://livepantau.semarangkota.go.id/c83dfda9-1e9e-4b8a-8c83-f7396d7781e4/index.m3u8",
        "lat": -6.9866287,
        "lng": 110.3750852,
        "route_order": 3,
        "route": "arterial",
        "zone": "Barat / Arteri Siliwangi",
    },
    {
        "camera_id": "KB01",
        "name": "KALIBANTENG",
        "url": "https://livepantau.semarangkota.go.id/14692ada-0bf1-4da9-bd4f-13a926804958/index.m3u8",
        "lat": -6.9845739,
        "lng": 110.3835144,
        "route_order": 4,
        "route": "arterial",
        "zone": "Barat-Pusat / Flyover Bandara",
    },
    {
        "camera_id": "KG01",
        "name": "KARANGAYU KE TIMUR",
        "url": "https://livepantau.semarangkota.go.id/fcd5964e-b58b-48f5-b6f0-3e9af143f5c8/index.m3u8",
        "lat": -6.9825473,
        "lng": 110.3917226,
        "route_order": 5,
        "route": "arterial",
        "zone": "Barat-Pusat / Koridor Papandayan",
    },
    {
        "camera_id": "IB01",
        "name": "INDRAPRASTA-IMAM BONJOL",
        "url": "https://livepantau.semarangkota.go.id/0b44f5b2-780d-4f86-9ecd-801041b8925a/index.m3u8",
        "lat": -6.9785714,
        "lng": 110.4116360,
        "route_order": 6,
        "route": "arterial",
        "zone": "Pusat / Konektor ke CBD",
    },
    {
        "camera_id": "SP01",
        "name": "SIMPANG LIMA 2",
        "url": "https://livepantau.semarangkota.go.id/7af16225-3215-49b7-8966-d649a947960d/index.m3u8",
        "lat": -6.9897019,
        "lng": 110.4239394,
        "route_order": 7,
        "route": "arterial",
        "zone": "Pusat / CBD",
    },
    {
        "camera_id": "PH01",
        "name": "DPU_PAHLAWAN",
        "url": "https://livepantau.semarangkota.go.id/c954ee49-2de6-4e7e-be98-8e17c659f9a9/index.m3u8",
        "lat": -6.9922400,
        "lng": 110.4218597,
        "route_order": 8,
        "route": "arterial",
        "zone": "Pusat-Selatan / Koridor Pahlawan",
    },
    {
        "camera_id": "SW01",
        "name": "SRIWIJAYA 01",
        "url": "https://livepantau.semarangkota.go.id/8eb25438-c8d3-4c8d-98fd-be74d14df3fa/index.m3u8",
        "lat": -7.0014592,
        "lng": 110.4244136,
        "route_order": 9,
        "route": "arterial",
        "zone": "Pusat-Selatan / Peterongan",
    },
    {
        "camera_id": "KW01",
        "name": "KALIWIRU",
        "url": "https://livepantau.semarangkota.go.id/cbb3e887-84c4-43c7-9e70-913dc8f460fd/index.m3u8",
        "lat": -7.0234964,
        "lng": 110.4203931,
        "route_order": 10,
        "route": "arterial",
        "zone": "Selatan / Tanjakan Kaliwiru",
    },
    {
        "camera_id": "BS01",
        "name": "BUKIT SARI",
        "url": "https://livepantau.semarangkota.go.id/4ff40187-00a9-440f-9256-9c0a89af55aa/index.m3u8",
        "lat": -7.0438750,
        "lng": 110.4215776,
        "route_order": 11,
        "route": "arterial",
        "zone": "Selatan / Sendangmulyo-Tembalang",
    },
    {
        "camera_id": "JT01",
        "name": "FLY OVER JATINGALEH WIDE",
        "url": "https://livepantau.semarangkota.go.id/5b09107f-81a6-4e14-b9b7-7712ef5aef7a/index.m3u8",
        "lat": -7.0313796,
        "lng": 110.4181186,
        "route_order": 12,
        "route": "tol",
        "zone": "Selatan / Koridor Tol",
    },
    {
        "camera_id": "SR01",
        "name": "EXIT TOL SRONDOL",
        "url": "https://livepantau.semarangkota.go.id/c3814165-b28d-4a32-b33f-007a8e412003/index.m3u8",
        "lat": -7.0610319,
        "lng": 110.4136418,
        "route_order": 13,
        "route": "tol",
        "zone": "Selatan / Gerbang Tembalang",
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


def downscale(frame: np.ndarray) -> np.ndarray:
    h, w = frame.shape[:2]
    if w <= MAX_WIDTH:
        return frame
    scale = MAX_WIDTH / w
    return cv2.resize(frame, (MAX_WIDTH, round(h * scale)), interpolation=cv2.INTER_AREA)


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
    parser.add_argument("--interval", type=float, default=600.0, help="Seconds between capture cycles (default: 600)")
    parser.add_argument("--duration", type=float, default=0, help="Stop after N seconds; 0 means continuous run")
    parser.add_argument("--timeout", type=float, default=8.0, help="Per-camera stream read timeout in seconds")
    parser.add_argument("--output", type=Path, default=ROOT / "data_koridor")
    parser.add_argument("--threads", type=int, default=7, help="Concurrent capture threads")
    args = parser.parse_args()

    frames_dir = args.output / "raw_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output / "raw_cctv_metadata.csv"
    file_exists = csv_path.exists() and csv_path.stat().st_size > 0

    registry_path = args.output / "camera_registry.json"
    with registry_path.open("w", encoding="utf-8") as f:
        json.dump(CAMERAS, f, indent=2)

    csv_file = csv_path.open("a", newline="", encoding="utf-8")
    writer = csv.DictWriter(csv_file, fieldnames=FIELDS)
    if not file_exists:
        writer.writeheader()
        csv_file.flush()

    signal.signal(signal.SIGINT, stop_capture)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, stop_capture)

    frame_indices: dict[str, int] = {cam["camera_id"]: 0 for cam in CAMERAS}
    previous_hashes: dict[str, str] = {}

    if file_exists:
        with csv_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cid = row.get("camera_id")
                if cid in frame_indices:
                    frame_indices[cid] += 1
                if cid and row.get("sha256"):
                    previous_hashes[cid] = row["sha256"]

    print(f"============================================================", flush=True)
    print(f" Koridor Komuter Kaliwungu-Tembalang - Frame Collector", flush=True)
    print(f" Cameras        : {len(CAMERAS)} (route_order 1-{len(CAMERAS)})", flush=True)
    print(f" Cycle Interval : {args.interval:.1f}s", flush=True)
    print(f" Storage        : JPEG q{JPEG_QUALITY}, max width {MAX_WIDTH}px", flush=True)
    print(f" Output CSV     : {csv_path}", flush=True)
    print(f" Started At     : {datetime.now(JAKARTA).strftime('%Y-%m-%d %H:%M:%S WIB')}", flush=True)
    print(f" Press Ctrl+C at any time to stop safely.", flush=True)
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

            print(f"\n--- [Cycle #{cycle:03d} | {time_display} WIB] Polling {len(CAMERAS)} cameras ---", flush=True)

            results: list[dict] = []
            with ThreadPoolExecutor(max_workers=args.threads) as executor:
                futures = {
                    executor.submit(capture_single_camera, cam, args.timeout): cam
                    for cam in CAMERAS
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
                        "route_order": cam["route_order"],
                        "route": cam["route"],
                        "zone": cam["zone"],
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
                        frame = downscale(frame)
                        h, w = frame.shape[:2]
                        mean_lum, lap_var, dhash, sha = image_metrics(frame)
                        is_dup = (previous_hashes.get(cid) == sha)
                        previous_hashes[cid] = sha

                        frame_fname = f"{fid}.jpg"
                        frame_target = frames_dir / frame_fname
                        if cv2.imwrite(str(frame_target), frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]):
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
                            print(f"  [OK] #{cam['route_order']:02d} {cid:<4} {cname:<26} ({w}x{h}) | Lum={mean_lum:5.1f}{dup_flag}", flush=True)
                        else:
                            row["capture_status"] = "write_error"
                            print(f"  [ERR] #{cam['route_order']:02d} {cid:<4} {cname:<26} Disk write failed!", flush=True)
                    else:
                        print(f"  [OFFLINE] #{cam['route_order']:02d} {cid:<4} {cname:<26} Stream timed out", flush=True)

                    results.append(row)

            for r in results:
                writer.writerow(r)
            csv_file.flush()

            ok_count = sum(1 for r in results if r["capture_status"] == "captured")
            elapsed = time.monotonic() - cycle_start
            print(f"Cycle completed in {elapsed:.1f}s: {ok_count}/{len(CAMERAS)} frames captured.", flush=True)

            sleep_time = args.interval - elapsed
            if args.duration > 0:
                remaining = args.duration - (time.monotonic() - started)
                sleep_time = min(sleep_time, max(remaining, 0))
            if sleep_time > 0 and not STOP:
                time.sleep(sleep_time)

    finally:
        csv_file.close()
        print(f"\n[DONE] Collector session ended. Output: {args.output}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
