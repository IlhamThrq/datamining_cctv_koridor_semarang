@echo off
title CCTV ATCS Semarang - 12 Camera Live Collector
cd /d "%~dp0"
echo ============================================================
echo   Menjalankan Pengumpulan Data CCTV ATCS Kota Semarang
echo   Target: 12 Kamera Persimpangan (Simpang Lima, Tugu Muda, dll)
echo   Interval: 120 detik (2 menit)
echo   Output: data/raw_frames/ dan data/raw_cctv_metadata.csv
echo   Tekan Ctrl+C untuk berhenti kapan saja secara aman.
echo ============================================================
".venv\Scripts\python.exe" capture_multi_live.py --interval 120 %*
pause
