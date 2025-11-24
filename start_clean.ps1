# ReconRaven Clean Starter
# This script safely starts the system after checking for zombies

Write-Host "ReconRaven Clean Startup Script" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check for zombie processes on port 5000
Write-Host "[1/3] Checking for zombie processes on port 5000..." -ForegroundColor Yellow
$port5000 = netstat -ano | findstr ":5000.*LISTENING"
if ($port5000) {
    Write-Host "WARNING: Port 5000 is in use!" -ForegroundColor Red
    Write-Host $port5000
    $pid = ($port5000 -split '\s+')[-1]
    Write-Host "Killing process $pid..." -ForegroundColor Yellow
    Stop-Process -Id $pid -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Write-Host "Port cleared!" -ForegroundColor Green
} else {
    Write-Host "Port 5000 is clear!" -ForegroundColor Green
}

# Check SDR status
Write-Host ""
Write-Host "[2/3] Checking SDR status..." -ForegroundColor Yellow
cd D:\SIGINT-RTL-SDRProject
$sdrCount = python -c "from rtlsdr import librtlsdr; print(librtlsdr.rtlsdr_get_device_count())" 2>$null
if ($sdrCount) {
    Write-Host "Detected $sdrCount SDR(s)!" -ForegroundColor Green
} else {
    Write-Host "ERROR: No SDRs detected!" -ForegroundColor Red
    Write-Host "Please unplug and replug your SDRs, then run this script again." -ForegroundColor Yellow
    pause
    exit 1
}

# Start the system
Write-Host ""
Write-Host "[3/3] Starting ReconRaven..." -ForegroundColor Yellow
Write-Host "Dashboard will be available at: http://localhost:5000" -ForegroundColor Cyan
Write-Host ""
python reconraven.py scan --dashboard

