#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${DIR}/../.." && pwd)"
REPOSITORY="${DIR}/.workspace/NodeGoat"
REPORTS="${DIR}/reports"
CONFIG="${DIR}/codeguard.toml"
CODEGUARD_BIN="${ROOT}/.venv/bin/codeguard"
OPEN_REPORT=1

if [ "${1:-}" = "--no-open" ]; then
  OPEN_REPORT=0
fi

if [ ! -x "$CODEGUARD_BIN" ]; then
  CODEGUARD_BIN="$(command -v codeguard || true)"
fi
if [ -z "$CODEGUARD_BIN" ]; then
  echo "Error: CodeGuard is not installed. Activate the project virtual environment first."
  exit 1
fi

if [ ! -d "${REPOSITORY}/.git" ]; then
  echo "NodeGoat is not present; running setup first."
  bash "${DIR}/setup.sh"
fi

mkdir -p "$REPORTS"
COMMIT="$(git -C "$REPOSITORY" rev-parse HEAD)"

echo "================================================================================"
echo " REAL-WORLD DEMO: OWASP NodeGoat"
echo " Repository: https://github.com/OWASP/NodeGoat"
echo " Revision:   $COMMIT"
echo " Scope:      First-party JavaScript application code"
echo "================================================================================"
echo ""

echo "[1/4] Human-readable scan"
"$CODEGUARD_BIN" scan "$REPOSITORY" --config "$CONFIG" --jobs 1 --show-suppressed \
  --exit-zero --no-color | tee "${REPORTS}/nodegoat.txt"

echo "[2/4] JSON report"
"$CODEGUARD_BIN" scan "$REPOSITORY" --config "$CONFIG" --jobs 1 --format json \
  --show-suppressed --exit-zero -o "${REPORTS}/nodegoat.json"

echo "[3/4] SARIF report"
"$CODEGUARD_BIN" scan "$REPOSITORY" --config "$CONFIG" --jobs 1 --format sarif \
  --show-suppressed --exit-zero -o "${REPORTS}/nodegoat.sarif"

echo "[4/4] Presentation HTML"
python3 "${DIR}/render_report.py" \
  --input "${REPORTS}/nodegoat.json" \
  --repository "$REPOSITORY" \
  --commit "$COMMIT" \
  --output "${REPORTS}/nodegoat-report.html"

echo ""
echo "Reports written to: $REPORTS"

if [ "$OPEN_REPORT" -eq 1 ]; then
  if command -v open &> /dev/null && open -a "Google Chrome" "${REPORTS}/nodegoat-report.html"; then
    echo "Opened the HTML report in Google Chrome."
  elif command -v google-chrome &> /dev/null; then
    google-chrome "${REPORTS}/nodegoat-report.html" &> /dev/null &
    echo "Opened the HTML report in Google Chrome."
  else
    echo "Chrome was not opened automatically. Open: ${REPORTS}/nodegoat-report.html"
  fi
fi

