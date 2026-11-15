#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PY=".venv/bin/python"
if [[ ! -x "$PY" ]]; then echo 'Instala primero con: bash INSTALAR_MAC.sh'; exit 1; fi
"$PY" 00b_discover_sia_candidates.py
"$PY" 00c_catalogo_sia.py
"$PY" 00d_validate_multiepoch.py --detector D6 --per-epoch 3 --min-days 14 --threshold 0.25
"$PY" 06_science_routes.py --input outputs/catalogs/candidate_pairs_multiepoch_05.json --min-days 14
printf 'Resultados en outputs/validations/morley_science_routes.json\n'
