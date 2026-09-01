#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODEGUARD_BIN="${DIR}/../.venv/bin/codeguard"
if [ ! -f "$CODEGUARD_BIN" ]; then
  CODEGUARD_BIN="codeguard"
fi

if ! command -v "$CODEGUARD_BIN" &> /dev/null && [ ! -f "$CODEGUARD_BIN" ]; then
  echo "Error: CodeGuard binary not found. Please install codeguard-cli or activate .venv."
  exit 1
fi

print_menu() {
  echo ""
  echo "================================================================================"
  echo "                     CODEGUARD SHOWCASE DEMO SUITE                             "
  echo "================================================================================"
  echo " Select an HTML report to generate and open:"
  echo "   [1] Demo 1: Developer Inner-Loop"
  echo "   [2] Demo 2: Legacy Baseline Adoption"
  echo "   [3] Demo 3: Diff-Aware CI & SARIF"
  echo "   [4] Demo 4: Governed Suppressions"
  echo "   [5] Demo 5: Monorepo Policy"
  echo "   [6] Real-World Scan: OWASP NodeGoat (downloads on first run)"
  echo "   [A] Combined HTML Report for Demos 1-5"
  echo "   [Q] Quit"
  echo "================================================================================"
  printf " Enter selection [1-6, A, Q]: "
}

generate_html_report() {
  local selection="${1:-all}"
  local output="${2:-${DIR}/reports/codeguard-demo-report.html}"
  python3 "${DIR}/generate_html_report.py" "$selection" --output "$output"
  open_html_report "$output"
}

open_html_report() {
  local output="$1"

  if command -v open &> /dev/null; then
    if open -a "Google Chrome" "$output"; then
      echo "Opened report in Google Chrome."
      return
    fi
  elif command -v google-chrome &> /dev/null; then
    google-chrome "$output" &> /dev/null &
    echo "Opened report in Google Chrome."
    return
  elif command -v google-chrome-stable &> /dev/null; then
    google-chrome-stable "$output" &> /dev/null &
    echo "Opened report in Google Chrome."
    return
  fi

  echo "Report created, but Google Chrome could not be opened automatically."
}

run_demo_1() {
  bash "${DIR}/01_developer_inner_loop/run.sh"
}

run_demo_2() {
  bash "${DIR}/02_legacy_baseline/run.sh"
}

run_demo_3() {
  bash "${DIR}/03_ci_diff_and_sarif/run.sh"
}

run_demo_4() {
  bash "${DIR}/04_governed_suppressions/run.sh"
}

run_demo_5() {
  bash "${DIR}/05_monorepo_policy/run.sh"
}

run_demo_6() {
  bash "${DIR}/06_real_world_nodegoat/run.sh"
}

run_all() {
  run_demo_1
  echo ""
  read -p "Press [Enter] to proceed to Demo 2..."
  echo ""
  run_demo_2
  echo ""
  read -p "Press [Enter] to proceed to Demo 3..."
  echo ""
  run_demo_3
  echo ""
  read -p "Press [Enter] to proceed to Demo 4..."
  echo ""
  run_demo_4
  echo ""
  read -p "Press [Enter] to proceed to Demo 5..."
  echo ""
  run_demo_5
}

# Non-interactive argument handling
if [ "$#" -gt 0 ]; then
  case "$1" in
    1) run_demo_1 ;;
    2) run_demo_2 ;;
    3) run_demo_3 ;;
    4) run_demo_4 ;;
    5) run_demo_5 ;;
    6) run_demo_6 ;;
    all|a|A) run_all ;;
    --html|html|report)
      generate_html_report "${2:-all}" "${3:-${DIR}/reports/codeguard-demo-report.html}"
      ;;
    *) echo "Usage: $0 [1|2|3|4|5|6|all|--html [1|2|3|4|5|all] [output.html]]" ; exit 1 ;;
  esac
  exit 0
fi

# Interactive loop
while true; do
  print_menu
  read -r choice
  case "$choice" in
    1) generate_html_report 1 ;;
    2) generate_html_report 2 ;;
    3) generate_html_report 3 ;;
    4) generate_html_report 4 ;;
    5) generate_html_report 5 ;;
    6) run_demo_6 ;;
    a|A) generate_html_report all ;;
    q|Q) echo "Exiting demo suite. Happy coding!" ; exit 0 ;;
    *) echo "Invalid option, please try again." ;;
  esac
  echo ""
  read -p "Press [Enter] to return to menu..."
done
