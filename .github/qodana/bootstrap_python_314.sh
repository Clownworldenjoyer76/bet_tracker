#!/usr/bin/env bash
set -euo pipefail

ENV_DIR="/data/cache/conda/envs/bet_tracker_py314"

if [ ! -x "${ENV_DIR}/bin/python" ]; then
  . "${HOME}/.bashrc" 2>/dev/null || true
  conda create -y -p "${ENV_DIR}" python=3.14.5 pip
fi

PYTHON="${ENV_DIR}/bin/python"

"${PYTHON}" -m pip install --upgrade pip==26.2.1

"${PYTHON}" -m pip install   numpy==2.5.2   pandas==3.0.5   scipy==1.18.0   PyYAML==6.0.3   pyarrow==25.0.1   polars==1.44.2   scikit-learn==1.9.0   xgboost==3.4.1   lightgbm==4.6.0   requests==2.34.2   openpyxl==3.1.5   joblib==1.5.3   python-dateutil==2.9.0.post0   narwhals==2.26.0   tzdata==2026.3   playwright==1.62.0   pytz==2026.3.post1   nflreadpy==0.1.5   pytest==9.1.1   urllib3   beautifulsoup4

for package in   'sportsdataverse==0.0.75'   'nfl_data_py==0.3.3'   'catboost==1.2.10'
do
  if ! "${PYTHON}" -m pip install --no-deps --ignore-requires-python "${package}"; then
    echo "Optional Qodana analysis package unavailable: ${package}" >&2
  fi
done

"${PYTHON}" --version
"${PYTHON}" -c 'import sys; print(sys.executable)'

