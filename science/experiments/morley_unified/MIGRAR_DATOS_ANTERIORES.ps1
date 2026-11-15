param([Parameter(Mandatory=$true)][string]$Origen)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$Origen = (Resolve-Path $Origen).Path
$salidaAntigua = Join-Path $Origen 'outputs'
$salidaNueva = Join-Path $PSScriptRoot 'outputs'
if (-not (Test-Path $salidaAntigua)) { throw "No existe: $salidaAntigua" }
if ($Origen -eq $PSScriptRoot) { throw 'Origen y destino no pueden coincidir.' }
Write-Host 'Copiando solamente outputs (FITS, JSON, CSV y cache). No modifica los scripts.'
Copy-Item -Path (Join-Path $salidaAntigua '*') -Destination $salidaNueva -Recurse -Force
Write-Host 'Copia finalizada. Valida tamaños y archivos antes de borrar el origen.'
