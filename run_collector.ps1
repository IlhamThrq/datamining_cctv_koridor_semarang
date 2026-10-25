# Run Semarang ATCS Multi-Camera Live Collector
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " ATCS Kota Semarang - 12 Camera Live Collector" -ForegroundColor Green
Write-Host " Target   : 12 Kamera Persimpangan Utama" -ForegroundColor Yellow
Write-Host " Interval : 120 detik (1 frame / 2 menit per kamera)" -ForegroundColor Yellow
Write-Host " Output   : data/raw_frames/ dan data/raw_cctv_metadata.csv" -ForegroundColor Yellow
Write-Host " Tekan Ctrl+C untuk menghentikan sesi capture." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

& ".\.venv\Scripts\python.exe" capture_multi_live.py --interval 120 @args
