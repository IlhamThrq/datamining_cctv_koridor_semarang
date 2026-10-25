# Koleksi Data CCTV Koridor Komuter Kaliwungu–Tembalang (Semarang)

Kolektor frame CCTV publik untuk penelitian **penambangan pola spasial-temporal dan propagasi kemacetan pada koridor komuter Kaliwungu (Kendal) → Tembalang (Semarang)**. Sumber: portal CCTV publik Pemkot Semarang [pantausemar.semarangkota.go.id](https://pantausemar.semarangkota.go.id/). Koleksi berjalan 24/7 di GitHub Actions — laptop boleh mati.

## 13 Titik Koridor (terverifikasi aktif, semua kamera fixed non-PTZ/360)

| # | ID | Kamera | Zona | Rute | Resolusi |
|---|---|---|---|---|---|
| 1 | JR01 | Jrakah | Barat / Gerbang Kendal | arterial | 640×480 |
| 2 | KP01 | Counting Krapyak | Barat / Gerbang Tol Krapyak | arterial | 1600×900 |
| 3 | HN01 | Hanoman | Barat / Arteri Siliwangi | arterial | 1280×720 |
| 4 | KB01 | Kalibanteng | Barat-Pusat / Flyover Bandara | arterial | 352×288 |
| 5 | KG01 | Karangayu ke timur | Barat-Pusat / Papandayan | arterial | 1600×905 |
| 6 | IB01 | Indraprasta–Imam Bonjol | Pusat / Konektor CBD | arterial | 640×480 |
| 7 | SP01 | Simpang Lima 2 | Pusat / CBD | arterial | 704×576 |
| 8 | PH01 | DPU Pahlawan | Pusat-Selatan / Pahlawan | arterial | 640×360 |
| 9 | SW01 | Sriwijaya 01 | Pusat-Selatan / Peterongan | arterial | 1600×900 |
| 10 | KW01 | Kaliwiru | Selatan / Tanjakan Kaliwiru | arterial | 704×576 |
| 11 | BS01 | Bukit Sari | Selatan / Sendangmulyo-Tembalang | arterial | 1600×900 |
| 12 | JT01 | Fly Over Jatingaleh Wide | Selatan / Koridor Tol | tol | 1600×450 |
| 13 | SR01 | Exit Tol Srondol | Selatan / Gerbang Tembalang | tol | 1280×960 |

Kriteria pemilihan (tuliskan di metodologi paper): stratifikasi berurutan sepanjang koridor, hanya kamera fixed (PTZ/360 dieksklusi demi validitas perbandingan antar waktu), terverifikasi aktif. Registry lengkap: `data_koridor/camera_registry.json`.

## Cara menjalankan

### Mode 24/7 — GitHub Actions (laptop boleh mati)

Workflow `.github/workflows/collect.yml` menjalankan satu siklus capture tiap ~10 menit di server GitHub, lalu commit frame + CSV ke repo ini. Syarat: **repo publik** (menit Actions gratis tak terbatas).

Setup sekali:
1. Buat repo publik baru di GitHub, lalu push folder ini:
   ```powershell
   git init
   git add .
   git commit -m "corridor collector init"
   git remote add origin https://github.com/USERNAME/REPO.git
   git push -u origin main
   ```
2. Buka tab **Actions** → enable workflow "Collect Corridor Frames". Koleksi dimulai otomatis di jadwal cron berikutnya (bisa juga klik "Run workflow" untuk tes langsung).

Menghentikan koleksi setelah 1 minggu: tab **Actions** → pilih workflow → ⋯ → "Disable workflow".
Memindahkan hasil ke laptop: `git pull`.

### Mode lokal (alternatif; jangan dijalankan bersamaan dengan Actions)

```powershell
.\run_collector_koridor.bat          # interval 600 detik
# atau:
python capture_koridor.py --interval 600
```

## Spesifikasi data

- **Sampling**: 1 frame/kamera/~10 menit → 13.104 frame/minggu ≈ 1,6 GB (JPEG q80, lebar maks 1600px).
- **Timestamp**: WIB (`Asia/Jakarta`), ISO 8601 — jitter jadwal GitHub tercatat apa adanya di timestamp.
- **CSV** `data_koridor/raw_cctv_metadata.csv`: `frame_id`, `capture_timestamp`, `source_url`, `camera_id`, `camera_name`, `route_order`, `route`, `zone`, `capture_status`, `frame_path`, `resolution_w/h`, `mean_luminance`, `laplacian_variance`, `dhash_hex`, `sha256`, `is_duplicate_of_previous`, `vehicle_count`, `weather_condition`, `speed_estimate_kmh`.
- **Batas data**: `vehicle_count`, `weather_condition`, `speed_estimate_kmh` sengaja kosong — diisi hanya oleh inferensi model (rencana: YOLOv8) dan harus dilaporkan sebagai *estimasi berbasis model*, bukan angka faktual. Tidak ada metrik yang direkayasa.

## Rencana olah data (setelah 1 minggu koleksi)

1. Preprocessing: filter `capture_status != captured`, frame duplikat, malam-gelap ekstrem.
2. Inferensi YOLOv8 (pretrained COCO: car/motorcycle/bus/truck) → `vehicle_count`.
3. Indeks kemacetan per titik → klasterisasi profil harian (K-Means/K-Medoids + DTW, `tslearn`).
4. Korelasi silang berlag antar `route_order` berurutan → waktu propagasi kemacetan.

## Sejarah provenance

Folder project lama (12 titik versi awal, 21 Okt 2026, ±4 jam) kini menjadi backup terpisah di `D:\datamining\proyek_cctv_semarang\` — lihat `README_BACKUP.md` di sana. Seluruh CSV/frame/chart/presentasi dari draf sebelumnya mengandung metrik fabrikasi dan tidak boleh dipakai sebagai data observasi. Inventaris 64 stream pantausemar (`pantausemar_streams.json`) ikut repo ini — pakai untuk mencari URL pengganti jika ada stream yang rotasi/mati.
