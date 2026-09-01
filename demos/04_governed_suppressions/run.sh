#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODEGUARD_BIN="${DIR}/../../.venv/bin/codeguard"
if [ ! -f "$CODEGUARD_BIN" ]; then
  CODEGUARD_BIN="codeguard"
fi

TARGET="${DIR}/payments.py"

echo "================================================================================"
echo " DEMO 4: Governed Suppressions & Anti-Rot Auditing"
echo " Scenario: Preventing unchecked waivers, silent ignores, and security debt rot"
echo "================================================================================"
echo ""

echo "▶ STEP 1: Scan code with various suppression comments"
echo "  - Case 1: Valid suppression with 'reason:' -> cleanly suppressed."
echo "  - Case 2: Bare suppression WITHOUT 'reason:' -> triggers CG-META-001."
echo "  - Case 3: Temporary waiver with EXPIRED 'until=' -> triggers CG-META-002 and reactivates rule."
echo "  Command: codeguard scan demos/04_governed_suppressions/"
echo "--------------------------------------------------------------------------------"
"$CODEGUARD_BIN" scan "$TARGET" || true

echo ""
echo "▶ STEP 2: Audit ALL suppressions across the repository"
echo "  Inspect every active, expired, and unused suppression in one unified view."
echo "  Command: codeguard suppressions list demos/04_governed_suppressions/"
echo "--------------------------------------------------------------------------------"
"$CODEGUARD_BIN" suppressions list "$DIR"

echo ""
echo "▶ STEP 3: Continuous Governance — Fail CI on expired waivers"
echo "  Command: codeguard suppressions list demos/04_governed_suppressions/ --expired"
echo "--------------------------------------------------------------------------------"
"$CODEGUARD_BIN" suppressions list "$DIR" --expired || true

echo ""
echo "▶ STEP 4: Housekeeping — Identify unused/dead suppressions"
echo "  Finds comments where the underlying code was refactored and no longer needs a waiver."
echo "  Command: codeguard suppressions list demos/04_governed_suppressions/ --unused"
echo "--------------------------------------------------------------------------------"
"$CODEGUARD_BIN" suppressions list "$DIR" --unused

echo ""
echo "--------------------------------------------------------------------------------"
echo " KEY TAKEAWAYS & VALUE PROPOSITION:"
echo " 1. Zero 'Forever Waivers': Temporary waivers must have dates and reasons."
echo " 2. Audit Trail for Compliance: Instant SOC 2 / ISO 27001 evidence of security waivers."
echo " 3. Meta-Rule Enforcement: Prevents silent '# noqa' or '# ignore' blind spots."
echo " 4. Clean Codebase: Flags dead suppressions that are safe to delete."
echo "--------------------------------------------------------------------------------"
