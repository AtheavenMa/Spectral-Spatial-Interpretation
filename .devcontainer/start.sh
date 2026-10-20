#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if python - <<'PY'
from urllib.request import urlopen
try:
    with urlopen("http://127.0.0.1:7860/api/health", timeout=2) as response:
        assert response.status == 200
except Exception:
    raise SystemExit(1)
PY
then
  echo "SSI Playground already listening on port 7860."
else
  nohup python -m uvicorn lab.app:app --host 0.0.0.0 --port 7860     > /tmp/ssi-playground.log 2>&1 < /dev/null &
  echo "Starting SSI Playground on port 7860."
fi

echo "Open the forwarded port 7860 in GitHub Codespaces to use the Playground."
echo "Backend logs: /tmp/ssi-playground.log"
