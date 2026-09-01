#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODEGUARD_BIN="${DIR}/../../.venv/bin/codeguard"
if [ ! -f "$CODEGUARD_BIN" ]; then
  CODEGUARD_BIN="codeguard"
fi

CONFIG_FILE="${DIR}/codeguard.toml"

echo "================================================================================"
echo " DEMO 5: Centralized Policy & Monorepo Governance"
echo " Scenario: Tailoring security policy across different services in one monorepo"
echo "================================================================================"
echo ""

echo "▶ STEP 1: Validate policy-as-code configuration"
echo "  Command: codeguard validate --config demos/05_monorepo_policy/codeguard.toml"
echo "--------------------------------------------------------------------------------"
"$CODEGUARD_BIN" validate --config "$CONFIG_FILE"

echo ""
echo "▶ STEP 2: View the policy configuration (codeguard.toml)"
echo "  - Re-maps CG-SEC-001 to CRITICAL"
echo "  - Uses [[codeguard.overrides]] to disable CG-SEC-005 for scripts/**"
echo "--------------------------------------------------------------------------------"
cat "$CONFIG_FILE"

echo ""
echo "▶ STEP 3: Execute the scan with policy applied"
echo "  Command: codeguard scan demos/05_monorepo_policy/ --config .../codeguard.toml"
echo "--------------------------------------------------------------------------------"
"$CODEGUARD_BIN" scan "$DIR" --config "$CONFIG_FILE" || true

echo ""
echo "▶ STEP 4: Inspect suppressed findings with --show-suppressed"
echo "  Verifies that scripts/admin_tool.py was suppressed according to policy."
echo "--------------------------------------------------------------------------------"
"$CODEGUARD_BIN" scan "$DIR" --config "$CONFIG_FILE" --show-suppressed || true

echo ""
echo "--------------------------------------------------------------------------------"
echo " KEY TAKEAWAYS & VALUE PROPOSITION:"
echo " 1. Single Config Governance: Manage entire monorepo policies from one TOML file."
echo " 2. Risk-Based Severity: Escalate severity (e.g., HIGH -> CRITICAL) for core services."
echo " 3. Granular Path Overrides: Eliminate noise in test fixtures, scripts, or migrations."
echo " 4. Deterministic Validation: 'codeguard validate' catches config typos in CI."
echo "--------------------------------------------------------------------------------"
