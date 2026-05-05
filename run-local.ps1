param(
  [ValidateSet("app", "lightonocr", "both")]
  [string]$Service = "app",
  [string]$EnvName = "extract-pdf",
  [AllowEmptyString()]
  [ValidateSet("", "cpu", "gpu", "cuda", "auto")]
  [string]$Device = "",
  [switch]$Cpu,
  [switch]$Gpu
)

$ErrorActionPreference = "Stop"

function Require-CondaEnv {
  param([string]$Name)
  $json = conda env list --json | ConvertFrom-Json
  foreach ($prefix in $json.envs) {
    if ([System.IO.Path]::GetFileName($prefix) -eq $Name) {
      return $true
    }
  }
  return $false
}

function Show-LightOnOCRRuntimeInfo {
  $modelPath = if ($env:MODEL_PATH) { $env:MODEL_PATH } else { Join-Path $root "LightOnOCR-2-1B" }
  $device = if ($env:LIGHTONOCR_DEVICE) { $env:LIGHTONOCR_DEVICE } else { "auto" }
  $dtype = if ($env:LIGHTONOCR_DTYPE) { $env:LIGHTONOCR_DTYPE } else { "auto" }
  $logLevel = if ($env:LOG_LEVEL) { $env:LOG_LEVEL } else { "INFO" }

  Write-Host "[LightOnOCR Runtime]"
  Write-Host "  MODEL_PATH        = $modelPath"
  Write-Host "  LIGHTONOCR_DEVICE = $device"
  Write-Host "  LIGHTONOCR_DTYPE  = $dtype"
  Write-Host "  LOG_LEVEL         = $logLevel"

  $weights = Join-Path $modelPath "model.safetensors"
  if (-not (Test-Path $weights)) {
    Write-Host "[WARN] Khong tim thay file weights: $weights"
    Write-Host "       Server co the se khong khoi dong duoc neu MODEL_PATH sai."
  }

  Write-Host ""
  Write-Host "Luu y: lan dau load model co the mat vai phut tuy theo CPU/GPU."
  Write-Host "      Hay doi den khi thay log: 'Model san sang ...'"
  Write-Host ""
}

if (-not (Require-CondaEnv -Name $EnvName)) {
  Write-Host "[ERROR] Env '$EnvName' khong ton tai."
  Write-Host "Chay setup-all.ps1 truoc de tao env."
  exit 1
}

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$deviceArgs = @()
if ($Device) { $deviceArgs += $Device }
if ($Cpu) { $deviceArgs += "cpu" }
if ($Gpu) { $deviceArgs += "gpu" }

if ($deviceArgs.Count -gt 1) {
  Write-Host "[ERROR] Chi duoc chon mot device: -Device <cpu|gpu|cuda|auto>, -Cpu, hoac -Gpu."
  exit 1
}

if ($deviceArgs.Count -eq 1) {
  $env:LIGHTONOCR_DEVICE = $deviceArgs[0]
}

Write-Host ""
Write-Host "==============================================="
Write-Host "  Extract-PDF + LightOnOCR Local Runner"
Write-Host "  ENV_NAME = $EnvName"
Write-Host "  SERVICE  = $Service"
if ($deviceArgs.Count -eq 1) {
  Write-Host "  DEVICE   = $($deviceArgs[0])"
}
Write-Host "==============================================="
Write-Host ""

switch ($Service.ToLower()) {
  "app" {
    Write-Host "> Chay extract-pdf app server (port 8000)"
    Write-Host ""
    conda run --no-capture-output -n $EnvName python -m app.main
  }
  "lightonocr" {
    Write-Host "> Chay LightOnOCR API server (port 7861)"
    Write-Host ""
    Show-LightOnOCRRuntimeInfo
    Push-Location "LightOnOCR-2-1B"
    try {
      conda run --no-capture-output -n $EnvName python api.py
    }
    finally {
      Pop-Location
    }
  }
  "both" {
    Write-Host "> Chay extract-pdf + LightOnOCR cung luc"
    Write-Host "  - extract-pdf:  http://localhost:8000/ui"
    Write-Host "  - LightOnOCR:   http://localhost:7861/"
    Write-Host ""
    Show-LightOnOCRRuntimeInfo
    
    # Start extract-pdf in background
    Write-Host "Khoi dong extract-pdf..."
    $appJob = Start-Job -ScriptBlock {
      Set-Location $using:root
      conda run --no-capture-output -n $using:EnvName python -m app.main
    }
    
    Start-Sleep -Seconds 2
    
    # Start LightOnOCR in foreground
    Write-Host "Khoi dong LightOnOCR..."
    Push-Location "LightOnOCR-2-1B"
    try {
      conda run --no-capture-output -n $EnvName python api.py
    }
    finally {
      Pop-Location
      Stop-Job -Job $appJob
    }
  }
  default {
    Write-Host "Dung: .\run-local.ps1 [app|lightonocr|both] [-EnvName <env>] [-Cpu|-Gpu|-Device cpu|gpu|cuda|auto]"
    Read-Host "Press Enter to exit"
    exit 1
  }
}

Read-Host "Press Enter to exit"
