param(
  [string]$Name = "extract-pdf",
  [string]$PythonVersion = "3.10",
  [switch]$WithLightOnOCR,
  [switch]$ForceRecreate
)

$ErrorActionPreference = "Stop"

function Require-Conda {
  if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
    Write-Host "Khong tim thay lenh 'conda'. Hay cai Anaconda/Miniconda truoc."
    exit 1
  }
}

function Test-CondaEnvExists([string]$EnvName) {
  $json = conda env list --json | ConvertFrom-Json
  foreach ($prefix in $json.envs) {
    if ([System.IO.Path]::GetFileName($prefix) -eq $EnvName) {
      return $true
    }
  }
  return $false
}

Write-Host ""
Write-Host "==============================================="
Write-Host "  Build local Conda env for extract-pdf"
Write-Host "  ENV_NAME        = $Name"
Write-Host "  PYTHON_VERSION  = $PythonVersion"
Write-Host "  WITH_LIGHTONOCR = $WithLightOnOCR"
Write-Host "==============================================="
Write-Host ""

Require-Conda

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if ($ForceRecreate -and (Test-CondaEnvExists -EnvName $Name)) {
  Write-Host "> Xoa env cu: $Name"
  conda env remove -n $Name -y
}

if (-not (Test-CondaEnvExists -EnvName $Name)) {
  Write-Host "> Tao env moi: $Name (python=$PythonVersion)"
  conda create -n $Name -y python=$PythonVersion pip
}
else {
  Write-Host "> Env da ton tai: $Name"
}

Write-Host "> Cai dependencies chinh tu requirements.txt"
# conda run -n $Name python -m pip install --upgrade pip
conda run -n $Name python -m pip install -r requirements.txt

if ($WithLightOnOCR) {
  $lightReq = Join-Path $root "LightOnOCR-2-1B\requirements.txt"
  if (Test-Path $lightReq) {
    Write-Host "> Cai them dependencies LightOnOCR"
    conda run -n $Name python -m pip install -r $lightReq
  }
  else {
    Write-Host "> Khong tim thay $lightReq, bo qua"
  }
}

Write-Host ""
Write-Host "Hoan tat."
Write-Host "Kich hoat env: conda activate $Name"
Write-Host "Chay app:      python -m app.main"
Write-Host ""
Read-Host "Press Enter to exit"
