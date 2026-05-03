param(
  [string]$Name = "extract-pdf",
  [string]$PythonVersion = "3.10",
  [ValidateSet("cpu", "gpu")]
  [string]$Device = "gpu",
  [switch]$ForceRecreate
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$buildScript = Join-Path $root "build-conda.ps1"
$lightDir = Join-Path $root "LightOnOCR-2-1B"
$lightSetup = Join-Path $lightDir "setup_env.bat"

if (-not (Test-Path $buildScript)) {
  Write-Host "[ERROR] Khong tim thay script: $buildScript"
  exit 1
}

if (-not (Test-Path $lightSetup)) {
  Write-Host "[ERROR] Khong tim thay script: $lightSetup"
  exit 1
}

Write-Host ""
Write-Host "==============================================="
Write-Host "  Setup tong extract-pdf + LightOnOCR-2-1B"
Write-Host "  ENV_NAME       = $Name"
Write-Host "  PYTHON_VERSION = $PythonVersion"
Write-Host "  DEVICE_MODE    = $Device"
Write-Host "  FORCE_RECREATE = $ForceRecreate"
Write-Host "==============================================="
Write-Host ""

# Step 1: Build/update env cho extract-pdf
$buildArgs = @("-Name", $Name, "-PythonVersion", $PythonVersion)
if ($ForceRecreate) { $buildArgs += "-ForceRecreate" }

Write-Host "> Step 1/2: Build conda env cho extract-pdf"
& $buildScript @buildArgs
if ($LASTEXITCODE -ne 0) {
  Write-Host "[ERROR] Build env extract-pdf that bai."
  exit 1
}

# Step 2: Cai setup LightOnOCR trong cung env
Write-Host ""
Write-Host "> Step 2/2: Setup LightOnOCR-2-1B"
Push-Location $lightDir
try {
  $lightArgs = @("--name", $Name, "--python", $PythonVersion, "--$Device")
  & $lightSetup @lightArgs
  if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Setup LightOnOCR that bai."
    exit 1
  }
}
finally {
  Pop-Location
}

Write-Host ""
Write-Host "Hoan tat setup tong."
Write-Host "Kich hoat env: conda activate $Name"
Write-Host "Chay extract-pdf: python -m app.main"
Write-Host "Chay LightOnOCR API:"
Write-Host "  cd LightOnOCR-2-1B"
Write-Host "  python api.py"
Write-Host ""