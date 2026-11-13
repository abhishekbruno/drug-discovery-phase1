$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:VINA_EXECUTABLE = Join-Path $PSScriptRoot 'tools\vina.exe'
& (Join-Path $PSScriptRoot '.venv\Scripts\dockpipe.exe') ui
