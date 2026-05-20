#!/bin/bash
# =============================================================
# setup.sh — Main orchestrator
# Run this after: docker compose up -d
# =============================================================

set -e

SCRIPTS_DIR="$(dirname "$0")/scripts"

echo ""
echo "============================================================"
echo "  Corporate Network Setup"
echo "============================================================"

bash "$SCRIPTS_DIR/01_routers/run.sh"
bash "$SCRIPTS_DIR/02_hosts/run.sh"
bash "$SCRIPTS_DIR/03_routing/run.sh"
bash "$SCRIPTS_DIR/04_nat/run.sh"
bash "$SCRIPTS_DIR/05_firewall/run.sh"

echo ""
echo "============================================================"
echo "  Setup complete! Verify each step with:"
echo "    bash scripts/01_routers/test.sh"
echo "    bash scripts/02_hosts/test.sh"
echo "    bash scripts/03_routing/test.sh"
echo "    bash scripts/04_nat/test.sh"
echo "    bash scripts/05_firewall/test.sh"
echo "============================================================"
