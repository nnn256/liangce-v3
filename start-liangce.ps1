param([int]$Port=8810,[switch]$Lan)
$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
$python=Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) {
  python -m venv .venv
  $env:PYTHONUTF8='1'
  & $python -m pip install -r requirements.txt
  if ($LASTEXITCODE -ne 0) {throw 'Python dependencies failed'}
}
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'web/dist/index.html'))) {
  Push-Location frontend
  try {npm ci; if($LASTEXITCODE -ne 0){throw 'npm ci failed'}; npm run build; if($LASTEXITCODE -ne 0){throw 'frontend build failed'}} finally {Pop-Location}
}
$env:PYTHONUTF8='1'
$bind=if($Lan){'0.0.0.0'}else{'127.0.0.1'}
Write-Host "量测 v3: http://127.0.0.1:$Port"
if($Lan){Write-Host 'LAN mode enabled; use this computer LAN IP from your phone.'}
& $python -m uvicorn web.research_server:app --host $bind --port $Port
