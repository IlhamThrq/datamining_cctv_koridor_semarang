"""Capture timestamped frames and image-quality metadata from a public HLS stream.

No traffic counts, weather, speed, or other unobserved values are fabricated.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import signal
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
DEFAULT_STREAM = (
    "https://livepantau.semarangkota.go.id/"
    "7af16225-3215-49b7-8966-d649a947960d/video1_stream.m3u8"
)
JAKARTA = ZoneInfo("Asia/Jakarta")
STOP = False
FIELDS = [
    "frame_id", "capture_timestamp", "source_url", "camera_id", "camera_name",
    "capture_status", "frame_path", "resolution_w", "resolution_h",
    "mean_luminance", "laplacian_variance", "dhash_hex", "sha256",
    "is_duplicate_of_previous", "vehicle_count", "weather_condition", "speed_estimate_kmh",
]


def stop_capture(_signum, _frame):
    global STOP
    STOP = True


def open_stream(url: str) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def read_latest_frame(cap: cv2.VideoCapture, timeout: float) -> np.ndarray | None:
    """Drain buffered frames and return the newest decoded frame before timeout."""
    deadline = time.monotonic() + timeout
    newest = None
    while time.monotonic() < deadline:
        ok, frame = cap.read()
        if not ok or frame is None:
            if newest is not None:
                break
            time.sleep(0.25)
            continue
        newest = frame
        if time.monotonic() + 0.35 >= deadline:
            break
    return newest


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_STREAM, help="Public HLS URL")
    parser.add_argument("--camera-id", default="SP01")
    parser.add_argument("--camera-name", default="Simpang Lima 2")
    parser.add_argument("--interval", type=float, default=120.0, help="Seconds between scheduled captures")
    parser.add_argument("--duration", type=float, default=0, help="Stop after N seconds; 0 means run until interrupted")
    parser.add_argument("--read-timeout", type=float, default=20.0)
    parser.add_argument("--output", type=Path, default=ROOT / "data")
    args = parser.parse_args()
    if args.interval <= 0 or args.read_timeout <= 0 or args.duration < 0:
        parser.error("interval/read-timeout must be positive; duration cannot be negative")

    frames_dir = args.output / "raw_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output / "raw_cctv_metadata.csv"
    file_exists = csv_path.exists() and csv_path.stat().st_size > 0
    csv_file = csv_path.open("a", newline="", encoding="utf-8")
    writer = csv.DictWriter(csv_file, fieldnames=FIELDS)
    if not file_exists:
        writer.writeheader()
        csv_file.flush()

    signal.signal(signal.SIGINT, stop_capture)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, stop_capture)
    started = time.monotonic()
    next_capture = started
    with csv_path.open(encoding="utf-8") as existing_csv:
        frame_index = max(0, sum(1 for _ in existing_csv) - 1)
    previous_hashes: dict[str, str] = {}
    cap = None
    try:
        while not STOP and (args.duration == 0 or time.monotonic() - started < args.duration):
            delay = next_capture - time.monotonic()
            if delay > 0 and STOP:
                break
            if delay > 0:
                time.sleep(delay)
            captured_at = datetime.now(JAKARTA)
            frame_index += 1
            frame_id = f"{args.camera_id}_{captured_at:%Y%m%dT%H%M%S}_{frame_index:07d}"
            row = {
                "frame_id": frame_id,
                "capture_timestamp": captured_at.isoformat(timespec="seconds"),
                "source_url": args.url,
                "camera_id": args.camera_id,
                "camera_name": args.camera_name,
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
            if cap is None or not cap.isOpened():
                if cap is not None:
                    cap.release()
                cap = open_stream(args.url)
            frame = read_latest_frame(cap, args.read_timeout) if cap.isOpened() else None
            captured_at = datetime.now(JAKARTA)
            frame_id = f"{args.camera_id}_{captured_at:%Y%m%dT%H%M%S}_{frame_index:07d}"
            row["capture_timestamp"] = captured_at.isoformat(timespec="seconds")
            row["frame_id"] = frame_id
            if frame is not None:
                height, width = frame.shape[:2]
                mean_luminance, laplacian_variance, dhash, digest = image_metrics(frame)
                frame_path = frames_dir / f"{frame_id}.jpg"
                if cv2.imwrite(str(frame_path), frame):
                    row.update({
                        "capture_status": "captured",
                        "frame_path": str(frame_path.relative_to(args.output.parent)),
                        "resolution_w": width,
                        "resolution_h": height,
                        "mean_luminance": mean_luminance,
                        "laplacian_variance": laplacian_variance,
                        "dhash_hex": dhash,
                        "sha256": digest,
                        "is_duplicate_of_previous": str(previous_hashes.get(args.camera_id) == digest).lower(),
                    })
                    previous_hashes[args.camera_id] = digest
                    print(f"{row['capture_timestamp']} {args.camera_name}: captured {width}x{height}")
                else:
                    row["capture_status"] = "write_error"
            else:
                print(f"{row['capture_timestamp']} {args.camera_name}: stream unavailable; logging missing capture")
                if cap is not None:
                    cap.release()
                    cap = None
            writer.writerow(row)
            csv_file.flush()
            next_capture += args.interval
            if next_capture < time.monotonic():
                next_capture = time.monotonic() + args.interval
    finally:
        if cap is not None:
            cap.release()
        csv_file.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
