# configs\run.ps1

# 1) ルート解決（この ps1 の一つ上のフォルダ）
$root = Split-Path -Parent $PSScriptRoot

# 2) 入出力ファイル
$salaries = Join-Path $root 'data\raw\DKSalaries.csv'
$outCsv   = Join-Path $root 'data\processed\dk_import.csv'

# 3) ログ
$logsDir  = Join-Path $root 'logs'
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
$logPath  = Join-Path $logsDir ("run_{0:yyyyMMdd_HHmmss}.log" -f (Get-Date))

# 4) 解析・実行時に src を解決できるように
$env:PYTHONPATH = ($env:PYTHONPATH, (Join-Path $root 'src')) -join ';'

# 5) 早期ガード（ここで null やパス間違いを検知）
if (-not (Test-Path $salaries)) {
  Write-Error "Salaries CSV not found: $salaries"
  exit 1
}
# 出力先フォルダが無ければ作成
$null = New-Item -ItemType Directory -Force -Path (Split-Path -Parent $outCsv)

# 6) 参照用の表示（トラブル時に便利）
"root      = $root"
"salaries  = $salaries"
"outCsv    = $outCsv"
"log       = $logPath"

# 7) 実行
python (Join-Path $root 'run.py') `
  --salaries $salaries `
  --out $outCsv `
  --filter-il-out `
  --probable-pitchers `
  --archive `
| Tee-Object -FilePath $logPath -Append

# 8) 追加の確認（不要なら削除可）
(Get-Content $salaries -TotalCount 5) | Write-Host
