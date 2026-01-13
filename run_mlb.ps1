#requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# どこで実行しても相対パスが崩れないように
Set-Location -LiteralPath $PSScriptRoot

# ========== 設定 ==========
$dkCsv        = "data\raw\DKSalaries.csv"
$templateCsv  = "data\raw\dk_template.csv"
$playersCsv   = "data\processed\players_today.csv"
$lineupsCsv   = ".\lineups_multi.csv"
$dkImportCsv  = ".\dk_import.csv"
$rankEvCsv    = ".\rank_ev.csv"
$submitCsv    = ".\submit_lineups.csv"
$cap          = 50000
$topN         = 20

# ========== Transcript ==========
$logsDir = Join-Path $PSScriptRoot 'logs'
New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
$logPath = Join-Path $logsDir ("{0:yyyyMMdd_HHmmss}.txt" -f (Get-Date))

$sw = [System.Diagnostics.Stopwatch]::StartNew()
$transcribing = $false

try {
    Start-Transcript -Path $logPath
    $transcribing = $true

    Write-Host "=== MLB pipeline start ===" -ForegroundColor Cyan

    # 入力チェック
    $need = $dkCsv, $templateCsv, $playersCsv
    $missing = $need | Where-Object { -not (Test-Path $_) }
    if ($missing.Count) { throw "Missing files: $($missing -join ', ')" }

    # 1) lineup生成
    python .\make_lineups_multi.py
    '{0} rows in {1}' -f ((Import-Csv $lineupsCsv).Count), $lineupsCsv | Write-Host

    # 2) DKインポートCSV
    python .\make_dk_import.py `
      --template $templateCsv `
      --dk $dkCsv `
      --players $playersCsv `
      --lineups $lineupsCsv `
      --cap $cap `
      --out $dkImportCsv

    # 3) EV計算
    python .\simulate_lineups.py --dk $dkImportCsv --out $rankEvCsv

    # プレビュー
    Write-Host "`nTOP EV preview:" -ForegroundColor Yellow
    Import-Csv $rankEvCsv |
      Sort-Object ev -Descending |
      Select-Object -First 5 lineup_id,total_salary,ev,std,p90 | Format-Table

    # 4) 提出用CSV出力
    python .\select_and_export.py --in $rankEvCsv --out $submitCsv --top $topN

    # サマリ
    Get-Item $lineupsCsv, $dkImportCsv, $rankEvCsv, $submitCsv |
      Select-Object Name, Length, LastWriteTime | Format-Table
}
catch {
    Write-Error $_
    exit 1
}
finally {
    if ($transcribing) { Stop-Transcript }
    Write-Host ("READY: Upload {0} to DraftKings ({1:n1}s)" -f $submitCsv, $sw.Elapsed.TotalSeconds) -ForegroundColor Green
}
