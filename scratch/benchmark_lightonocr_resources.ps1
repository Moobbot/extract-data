param(
  [string]$DatasetDir = "D:\Work\Clients\A_Giap\extract-pdf\datasets\Quet so bang-1-5",
  [string]$Endpoint = "http://localhost:7861/extract",
  [int]$MaxTokens = 1024,
  [string]$OutputDir = "D:\Work\Clients\A_Giap\extract-pdf\outputs\benchmarks"
)

$ErrorActionPreference = "Stop"

function Convert-ToMiB {
  param([string]$Value)
  if ([string]::IsNullOrWhiteSpace($Value)) { return $null }

  $match = [regex]::Match($Value.Trim(), '^([0-9]+(?:\.[0-9]+)?)\s*([KMG]i?B)$')
  if (-not $match.Success) { return $null }

  $num = [double]$match.Groups[1].Value
  $unit = $match.Groups[2].Value

  switch ($unit) {
    "KiB" { return $num / 1024.0 }
    "MiB" { return $num }
    "GiB" { return $num * 1024.0 }
    default { return $null }
  }
}

function Get-GpuSample {
  $line = & nvidia-smi --query-gpu=utilization.gpu, memory.used, memory.total, power.draw --format=csv, noheader, nounits 2>$null | Select-Object -First 1
  if (-not $line) {
    return [pscustomobject]@{
      gpu_util_pct      = $null
      gpu_mem_used_mib  = $null
      gpu_mem_total_mib = $null
      gpu_power_w       = $null
    }
  }

  $parts = $line.Split(',') | ForEach-Object { $_.Trim() }
  return [pscustomobject]@{
    gpu_util_pct      = [double]$parts[0]
    gpu_mem_used_mib  = [double]$parts[1]
    gpu_mem_total_mib = [double]$parts[2]
    gpu_power_w       = [double]$parts[3]
  }
}

function Get-ContainerSample {
  $line = docker stats lightonocr --no-stream --format "{{.CPUPerc}}|{{.MemUsage}}" 2>$null
  if (-not $line) {
    return [pscustomobject]@{
      ctr_cpu_pct       = $null
      ctr_mem_used_mib  = $null
      ctr_mem_limit_mib = $null
    }
  }

  $parts = $line.Split('|')
  $cpuText = $parts[0].Trim().TrimEnd('%')
  $memText = $parts[1].Trim()

  $memParts = $memText.Split('/')
  $memUsed = Convert-ToMiB ($memParts[0].Trim())
  $memLimit = Convert-ToMiB ($memParts[1].Trim())

  return [pscustomobject]@{
    ctr_cpu_pct       = [double]$cpuText
    ctr_mem_used_mib  = $memUsed
    ctr_mem_limit_mib = $memLimit
  }
}

function Start-OcrJob {
  param(
    [string]$FilePath,
    [string]$TargetEndpoint,
    [int]$Tokens
  )

  return Start-Job -ScriptBlock {
    param($f, $ep, $t)
    $start = Get-Date
    $statusCode = & curl.exe -s -o NUL -w "%{http_code}" -X POST -F "file=@$f" -F "page_num=1" -F "max_tokens=$t" $ep
    $end = Get-Date
    [pscustomobject]@{
      file        = [System.IO.Path]::GetFileName($f)
      status_code = [int]$statusCode
      started_at  = $start
      ended_at    = $end
      duration_s  = ($end - $start).TotalSeconds
    }
  } -ArgumentList $FilePath, $TargetEndpoint, $Tokens
}

function Run-Scenario {
  param(
    [string]$Name,
    [string[]]$Files,
    [string]$TargetEndpoint,
    [int]$Tokens
  )

  $jobs = @()
  foreach ($f in $Files) {
    $jobs += Start-OcrJob -FilePath $f -TargetEndpoint $TargetEndpoint -Tokens $Tokens
  }

  $samples = New-Object System.Collections.Generic.List[object]
  $wallStart = Get-Date

  while (($jobs | Where-Object { $_.State -eq "Running" }).Count -gt 0) {
    $gpu = Get-GpuSample
    $ctr = Get-ContainerSample

    $samples.Add([pscustomobject]@{
        timestamp         = (Get-Date).ToString("o")
        scenario          = $Name
        gpu_util_pct      = $gpu.gpu_util_pct
        gpu_mem_used_mib  = $gpu.gpu_mem_used_mib
        gpu_mem_total_mib = $gpu.gpu_mem_total_mib
        gpu_power_w       = $gpu.gpu_power_w
        ctr_cpu_pct       = $ctr.ctr_cpu_pct
        ctr_mem_used_mib  = $ctr.ctr_mem_used_mib
        ctr_mem_limit_mib = $ctr.ctr_mem_limit_mib
      }) | Out-Null

    Wait-Job -Job $jobs -Any -Timeout 1 | Out-Null
  }

  $jobResults = @()
  foreach ($j in $jobs) {
    $jobResults += Receive-Job -Job $j
    Remove-Job -Job $j | Out-Null
  }

  $wallEnd = Get-Date

  $okCount = ($jobResults | Where-Object { $_.status_code -eq 200 }).Count
  $durations = $jobResults | Select-Object -ExpandProperty duration_s
  $durAvg = if ($durations.Count -gt 0) { ($durations | Measure-Object -Average).Average } else { $null }
  $durMax = if ($durations.Count -gt 0) { ($durations | Measure-Object -Maximum).Maximum } else { $null }

  $gpuMems = $samples | Where-Object { $_.gpu_mem_used_mib -ne $null } | Select-Object -ExpandProperty gpu_mem_used_mib
  $gpuUtils = $samples | Where-Object { $_.gpu_util_pct -ne $null } | Select-Object -ExpandProperty gpu_util_pct
  $ctrMems = $samples | Where-Object { $_.ctr_mem_used_mib -ne $null } | Select-Object -ExpandProperty ctr_mem_used_mib
  $ctrCpus = $samples | Where-Object { $_.ctr_cpu_pct -ne $null } | Select-Object -ExpandProperty ctr_cpu_pct

  return [pscustomobject]@{
    scenario               = $Name
    concurrency            = $Files.Count
    files                  = ($Files | ForEach-Object { [System.IO.Path]::GetFileName($_) }) -join ", "
    wall_time_s            = [math]::Round(($wallEnd - $wallStart).TotalSeconds, 2)
    request_avg_s          = if ($durAvg -ne $null) { [math]::Round($durAvg, 2) } else { $null }
    request_max_s          = if ($durMax -ne $null) { [math]::Round($durMax, 2) } else { $null }
    ok_requests            = $okCount
    total_requests         = $jobResults.Count
    gpu_mem_peak_mib       = if ($gpuMems.Count -gt 0) { [math]::Round(($gpuMems | Measure-Object -Maximum).Maximum, 2) } else { $null }
    gpu_util_avg_pct       = if ($gpuUtils.Count -gt 0) { [math]::Round(($gpuUtils | Measure-Object -Average).Average, 2) } else { $null }
    gpu_util_peak_pct      = if ($gpuUtils.Count -gt 0) { [math]::Round(($gpuUtils | Measure-Object -Maximum).Maximum, 2) } else { $null }
    container_mem_peak_mib = if ($ctrMems.Count -gt 0) { [math]::Round(($ctrMems | Measure-Object -Maximum).Maximum, 2) } else { $null }
    container_cpu_avg_pct  = if ($ctrCpus.Count -gt 0) { [math]::Round(($ctrCpus | Measure-Object -Average).Average, 2) } else { $null }
    container_cpu_peak_pct = if ($ctrCpus.Count -gt 0) { [math]::Round(($ctrCpus | Measure-Object -Maximum).Maximum, 2) } else { $null }
  }
}

New-Item -Path $OutputDir -ItemType Directory -Force | Out-Null

$images = Get-ChildItem -Path $DatasetDir -File |
Where-Object { $_.Extension -match '^\.(jpg|jpeg|png|bmp|webp)$' } |
Sort-Object Name |
Select-Object -ExpandProperty FullName

if ($images.Count -lt 3) {
  throw "Can benchmark needs at least 3 image files in $DatasetDir"
}

$scenarios = @(
  @{ name = "single"; files = @($images[0]) },
  @{ name = "parallel_2"; files = @($images[0], $images[1]) },
  @{ name = "parallel_3"; files = @($images[0], $images[1], $images[2]) }
)

$summary = @()
foreach ($sc in $scenarios) {
  Write-Host "Running scenario:" $sc.name
  $summary += Run-Scenario -Name $sc.name -Files $sc.files -TargetEndpoint $Endpoint -Tokens $MaxTokens
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$summaryPath = Join-Path $OutputDir ("summary_" + $stamp + ".csv")
$summary | Export-Csv -Path $summaryPath -NoTypeInformation -Encoding UTF8

$summary | Format-Table -AutoSize
Write-Host "Saved summary:" $summaryPath
