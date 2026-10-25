"""Package dataset and notebook into a lightweight zip for Google Colab."""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
zip_path = ROOT / "colab_bundle.zip"

files_to_pack = [
    ROOT / "CCTV_Semarang_Preprocessing.ipynb",
    ROOT / "data" / "raw_cctv_metadata.csv",
    ROOT / "data" / "clean_cctv_metadata.csv",
    ROOT / "data" / "cameras.csv",
    ROOT / "data" / "camera_registry.json"
]

with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for f in files_to_pack:
        if f.exists():
            z.write(f, arcname=f.relative_to(ROOT))
            print(f"Added {f.name} ({f.stat().st_size} bytes)")

    # Add a representative sample of raw frames (up to 2 frames per camera)
    frames_dir = ROOT / "data" / "raw_frames"
    cams_seen = {}
    if frames_dir.exists():
        for frame in sorted(frames_dir.glob("*.jpg")):
            cid = frame.name.split("_")[0]
            if cams_seen.get(cid, 0) < 2:
                cams_seen[cid] = cams_seen.get(cid, 0) + 1
                z.write(frame, arcname=f"data/raw_frames/{frame.name}")
                print(f"Added sample frame: {frame.name}")

print(f"\n[DONE] Colab bundle created: {zip_path} ({zip_path.stat().st_size / (1024*1024):.2f} MB)")
