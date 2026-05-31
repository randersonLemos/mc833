#!/bin/bash
# =============================================================
# setup.sh — Main orchestrator
# Run this after: docker compose up -d
# =============================================================

set -e

SCRIPTS_DIR="$(dirname "$0")/scripts"

echo ""
echo "============================================================"
echo "  Configuração da Rede Corporativa"
echo "============================================================"

bash "$SCRIPTS_DIR/01_routers/run.sh"
bash "$SCRIPTS_DIR/01_routers/test.sh"

bash "$SCRIPTS_DIR/02_hosts/run.sh"
bash "$SCRIPTS_DIR/02_hosts/test.sh"

bash "$SCRIPTS_DIR/03_routing/run.sh"
bash "$SCRIPTS_DIR/03_routing/test.sh"

bash "$SCRIPTS_DIR/04_nat/run.sh"
bash "$SCRIPTS_DIR/04_nat/test.sh"

bash "$SCRIPTS_DIR/05_firewall/run.sh"
bash "$SCRIPTS_DIR/05_firewall/test.sh"

echo ""
echo "============================================================"
echo "  Configuração concluída. Todos os testes passaram."
echo "============================================================"
