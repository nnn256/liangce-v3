$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:LIANGCE_TDX_BINARY=Join-Path $PSScriptRoot '.runtime/tdx-api-build/liangce-tdx-hosts.exe'
$env:LIANGCE_TDX_PORT='18089'
$env:LIANGCE_RUNTIME=Join-Path $PSScriptRoot '.runtime/local-signal-audit'
& (Join-Path $PSScriptRoot '.venv/Scripts/python.exe') -m uvicorn web.hosted_server:app --host 127.0.0.1 --port 8850 --workers 1 --log-level warning
