#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODEGUARD_BIN="${DIR}/../../.venv/bin/codeguard"
if [ ! -f "$CODEGUARD_BIN" ]; then
  CODEGUARD_BIN="codeguard"
fi

echo "================================================================================"
echo " DEMO 1: Developer Inner-Loop (Fast, Multi-Language Static Security Scan)"
echo " Scenario: Scanning a fullstack repo (Python API + TypeScript / React)"
echo " Command:  codeguard scan demos/01_developer_inner_loop/"
echo "================================================================================"
echo ""

"$CODEGUARD_BIN" scan "$DIR" || true

echo ""
echo "--------------------------------------------------------------------------------"
echo " KEY TAKEAWAYS & VALUE PROPOSITION:"
echo " 1. Instant Speed (<50ms): Zero delay for developer workflow."
echo " 2. Multi-Language: Analyzes Python AST and TypeScript Tree-sitter in one pass."
echo " 3. Actionable: Not just warning flags — exact carets (^) and plain-English fixes."
echo " 4. 100% Offline: No source code leaves the machine; zero external API dependencies."
echo "--------------------------------------------------------------------------------"
