param(
    [switch] $Offline,
    [int] $PerEpoch = 3,
    [double] $MinDays = 14,
    [double] $Threshold = 0.25
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$py = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) {
    throw 'Falta .venv. Ejecuta primero: .\INSTALAR_WINDOWS.ps1 (o python -m venv .venv y pip install -r requirements.txt).'
}
function Run-Step {
    param([string] $Name, [string[]] $Arguments)
    Write-Host "`n=== $Name ===" -ForegroundColor Cyan
    & $py @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Fallo $Name con codigo $LASTEXITCODE; el pipeline se detuvo para proteger datos." }
}
if (-not $Offline) {
    Run-Step '00B SIA2' @('00b_discover_sia_candidates.py')
    Run-Step '00C INVENTARIO' @('00c_catalogo_sia.py')
} elseif (-not (Test-Path '.\outputs\catalogs\spherex_sia_inventory.csv')) {
    throw 'Modo Offline: falta el CSV de 00C. Primero copia outputs antiguos o ejecuta 00B y 00C con Internet.'
} else {
    Write-Host 'Offline: reutilizando inventario 00C ya presente.'
}
$cmd00d = @('00d_validate_multiepoch.py', '--detector', 'D6', '--per-epoch', [string]$PerEpoch, '--min-days', [string]$MinDays, '--threshold', [string]$Threshold)
if ($Offline) { $cmd00d += '--offline' }
Run-Step '00D MULTIEPOCA' $cmd00d
Run-Step '06 SCIENCE ROUTES' @('06_science_routes.py', '--input', '.\outputs\catalogs\candidate_pairs_multiepoch_05.json', '--min-days', [string]$MinDays)
Write-Host "`nPipeline finalizado. Ver: outputs\validations\morley_science_routes.json" -ForegroundColor Green
Write-Host 'NO significa que haya movimiento ni ZOGY ejecutado.'
