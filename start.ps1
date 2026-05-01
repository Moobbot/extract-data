# start.ps1 — Tự động chọn CPU/GPU dựa trên LIGHTONOCR_DEVICE trong .env
#
# Cách dùng:
#   .\start.ps1              — khởi động (tự detect, GPU là mặc định)
#   .\start.ps1 down         — dừng tất cả services
#   .\start.ps1 logs         — xem logs
#   .\start.ps1 -Build       — rebuild image trước khi start
#
# Logic:
#   LIGHTONOCR_DEVICE=cpu  → docker-compose.cpu.yml (không cần nvidia)
#   LIGHTONOCR_DEVICE=*    → docker-compose.yml (mặc định GPU)

param(
    [Parameter(Position=0)]
    [string]$Command = "up",
    [switch]$Build
)

# ── Đọc LIGHTONOCR_DEVICE từ .env ──────────────────────────────────────────
$device = "auto"
if (Test-Path ".env") {
    $line = Get-Content ".env" | Where-Object { $_ -match "^\s*LIGHTONOCR_DEVICE\s*=" } | Select-Object -Last 1
    if ($line) {
        $device = ($line -split "=", 2)[1].Trim().Trim('"').ToLower()
    }
}

Write-Host ""
Write-Host "=================================================="
Write-Host "  Extract-PDF + LightOnOCR Startup"
Write-Host "  LIGHTONOCR_DEVICE = $device"
Write-Host "=================================================="

# ── Chọn compose file theo device ───────────────────────────────────────────
if ($device -eq "cpu") {
    $composeArgs = @("-f", "docker-compose.cpu.yml")
    Write-Host "  Mode: CPU  (file: docker-compose.cpu.yml)"
    Write-Host "  RAM:  Cần ≥ 12 GB cho Docker Desktop (WSL2)"
} else {
    $composeArgs = @("-f", "docker-compose.yml")
    Write-Host "  Mode: GPU  (file: docker-compose.yml)"
    Write-Host "  Yêu cầu: nvidia-container-toolkit"
}
Write-Host "=================================================="
Write-Host ""

$baseArgs = @("compose") + $composeArgs + @("--profile", "lightonocr")

switch ($Command.ToLower()) {
    "up" {
        $upArgs = $baseArgs + @("up", "-d")
        if ($Build) { $upArgs += "--build" }
        Write-Host "Chạy: docker $($upArgs -join ' ')"
        Write-Host ""
        & docker @upArgs
    }
    "down" {
        & docker @($baseArgs + "down")
    }
    "logs" {
        & docker @($baseArgs + "logs" + "-f")
    }
    "restart" {
        & docker @($baseArgs + "restart")
    }
    "ps" {
        & docker @($baseArgs + "ps")
    }
    default {
        Write-Host "Dùng: .\start.ps1 [up|down|logs|restart|ps] [-Build]"
        exit 1
    }
}
