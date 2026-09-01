#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODEGUARD_BIN="${DIR}/../../.venv/bin/codeguard"
if [ ! -f "$CODEGUARD_BIN" ]; then
  CODEGUARD_BIN="codeguard"
fi

BASELINE_FILE="${DIR}/.codeguard-baseline.json"
NEW_FEATURE_FILE="${DIR}/new_feature.py"

cleanup() {
  rm -f "$BASELINE_FILE" "$NEW_FEATURE_FILE"
}
trap cleanup EXIT

echo "================================================================================"
echo " DEMO 2: 'Stop the Bleeding' Legacy Baseline Adoption"
echo " Scenario: Adopting CodeGuard on Day 1 in a large legacy codebase"
echo "================================================================================"
echo ""

echo "▶ STEP 1: Scan the legacy codebase without a baseline"
echo "  Command: codeguard scan demos/02_legacy_baseline/"
echo "--------------------------------------------------------------------------------"
"$CODEGUARD_BIN" scan "$DIR" || true

echo ""
echo "▶ STEP 2: The dilemma — In traditional SAST, these 2 findings would BREAK CI"
echo "  and delay shipping. With CodeGuard, snapshot existing debt into a baseline:"
echo "  Command: codeguard baseline create demos/02_legacy_baseline/ -o .codeguard-baseline.json"
echo "--------------------------------------------------------------------------------"
"$CODEGUARD_BIN" baseline create "$DIR" -o "$BASELINE_FILE"

echo ""
echo "▶ STEP 3: Rescan with the baseline applied"
echo "  Command: codeguard scan demos/02_legacy_baseline/ --baseline .codeguard-baseline.json"
echo "--------------------------------------------------------------------------------"
"$CODEGUARD_BIN" scan "$DIR" --baseline "$BASELINE_FILE"

echo ""
echo "▶ STEP 4: Developer opens a PR adding a new feature with a shell injection"
echo "  Creating new_feature.py in the active sprint..."
cat << 'PYEOF' > "$NEW_FEATURE_FILE"
import subprocess

def run_backup(target_dir: str):
    # CG-SEC-005: Newly introduced command injection
    subprocess.run(f"tar -czf backup.tar.gz {target_dir}", shell=True)
PYEOF

echo "  Command: codeguard scan demos/02_legacy_baseline/ --baseline .codeguard-baseline.json"
echo "--------------------------------------------------------------------------------"
"$CODEGUARD_BIN" scan "$DIR" --baseline "$BASELINE_FILE" || true

echo ""
echo "--------------------------------------------------------------------------------"
echo " KEY TAKEAWAYS & VALUE PROPOSITION:"
echo " 1. Day-1 Zero Friction: Legacy issues are frozen so teams can adopt immediately."
echo " 2. Net-New Enforcement: CI blocks ONLY newly introduced vulnerabilities."
echo " 3. Stable Fingerprints: AST fingerprints survive code formatting and line shifts."
echo " 4. Debt Burndown: 'codeguard baseline prune' ratchets down debt as fixes land."
echo "--------------------------------------------------------------------------------"
