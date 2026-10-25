@echo off
title CCTV Koridor Komuter Kaliwungu-Tembalang - 13 Kamera
cd /d "%~dp0"
echo ============================================================
echo   Kolektor CCTV Koridor Komuter Kaliwungu-Tembalang
echo   13 titik (route_order 1-13) | Interval 10 menit
echo   Output: data_koridor\raw_frames\ + data_koridor\raw_cctv_metadata.csv
echo.
echo   CATATAN: jalankan INI ATAU GitHub Actions, jangan keduanya
echo   bersamaan (frame akan dobel). Ctrl+C untuk berhenti aman.
echo ============================================================
".venv\Scripts\python.exe" capture_koridor.py --interval 600 %*
pause
