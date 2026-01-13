# run.ps1  --- プロジェクト直下に保存 ---
$ErrorActionPreference = 'Stop'

# スクリプトの場所（貼り付け実行でも動くようにフォールバック付き）
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $root) { $root = $PWD.Path }   # ← ここが重要（貼り付け実行対策）

# パス
$salaries = Join-Path $root 'data\raw\DKSalaries.csv'
$outFile  = Join-Path $root 'data\processed\dk_import.csv'
$logDir   = Join-Path $root 'logs'
$null = New-Item $logDir -ItemType Directory -Force
$log = Join-Path $logDir ("run_{0:yyyyMMdd_HHmmss}.log" -f (Get-Date))

"=== Run at $(Get-Date) ===" | Tee-Object -FilePath $log

# 入力 CSV の変更検知（ハッシュ）
$hashFile = Join-Path $logDir 'last_salaries.sha256'
$curHash  = (Get-FileHash $salaries -Algorithm SHA256).Hash
if (Test-Path $hashFile) {
  $oldHash = Get-Content $hashFile -ErrorAction SilentlyContinue
  if ($oldHash -eq $curHash) {
    "No change in DKSalaries.csv. Skip." | Tee-Object -FilePath $log -Append
    exit 0
  }
}
$curHash | Set-Content $hashFile

# Python 実行
$runpy = Join-Path $root 'run.py'
& python $runpy --salaries $salaries --out $outFile `
  --filter-il-out --probable-pitchers --archive `
  | Tee-Object -FilePath $log -Append
