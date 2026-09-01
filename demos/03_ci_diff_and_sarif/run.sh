#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODEGUARD_BIN="${DIR}/../../.venv/bin/codeguard"
if [ ! -f "$CODEGUARD_BIN" ]; then
  CODEGUARD_BIN="codeguard"
fi

TARGET="${DIR}/dirty_feature.py"

echo "================================================================================"
echo " DEMO 3: Diff-Aware CI Gating & Platform Integration (SARIF / GitHub Actions)"
echo " Scenario: Pull Request validation and security dashboard reporting"
echo "================================================================================"
echo ""

echo "▶ STEP 1: Inline GitHub Actions annotations (Default for 'codeguard ci')"
echo "  Renders PR annotations right on the developer's changed lines in GitHub."
echo "  Command: codeguard scan ... --format github"
echo "--------------------------------------------------------------------------------"
"$CODEGUARD_BIN" scan "$TARGET" --format github || true

echo ""
echo "▶ STEP 2: Native OASIS SARIF 2.1.0 (Feeds GitHub Security / GitLab Security Tab)"
echo "  Carries stable fingerprints, CWE tags, severity scores, and doc URLs."
echo "  Command: codeguard scan ... --format sarif"
echo "--------------------------------------------------------------------------------"
"$CODEGUARD_BIN" scan "$TARGET" --format sarif | head -n 35
echo "  ... (valid SARIF 2.1.0 payload truncated for display) ..."

echo ""
echo "▶ STEP 3: Multi-CI Formats: Reviewdog (rdjson) & JUnit (XML)"
echo "  Easily integrates with GitLab, Bitbucket, Azure DevOps, and Jenkins."
echo "  Command: codeguard scan ... --format rdjson"
echo "--------------------------------------------------------------------------------"
"$CODEGUARD_BIN" scan "$TARGET" --format rdjson | head -n 25
echo "  ... (rdjson payload truncated for display) ..."

echo ""
echo "--------------------------------------------------------------------------------"
echo " KEY TAKEAWAYS & VALUE PROPOSITION:"
echo " 1. Diff-Aware CI: 'codeguard ci' tests only modified files; PR checks take <2s."
echo " 2. Zero-Config GitHub Action: 'uses: mevichitra/codeguard/action@v2' works out of the box."
echo " 3. No Vendor Lock-In: Exports standard SARIF, GitHub annotations, RDJSON, and JUnit."
echo " 4. Security Hub Integration: Findings populate the GitHub Security Code Scanning tab."
echo "--------------------------------------------------------------------------------"
