#!/bin/bash
# =============================================================
# 02_hosts/test.sh — Verify all host IPs were assigned
#
# Checks every container for the expected IP using:
#   docker exec <container> ip addr show
# Prints [PASS] or [FAIL] for each check.
# =============================================================

PASS=0
FAIL=0

check() {
    local container=$1
    local expected_ip=$2
    local description=$3

    if docker exec "$container" ip addr show 2>/dev/null | grep -q "$expected_ip"; then
        printf "    [PASS] %-16s → %-18s %s\n" "$container" "$expected_ip" "$description"
        PASS=$((PASS + 1))
    else
        printf "    [FAIL] %-16s → %-18s %s\n" "$container" "$expected_ip" "$description"
        FAIL=$((FAIL + 1))
    fi
}

echo ""
echo "============================================================"
echo "  TEST 2 — Host IP Assignment Verification"
echo "============================================================"

# ── Corporate servers ──────────────────────────────────────────
echo ""
echo "  ┌─ Corporate Servers — net_servico (192.168.100.0/26) ┐"
echo "  │  Gateway: 192.168.100.1 (r1_hq eth1)                │"
echo "  └──────────────────────────────────────────────────────┘"
check srv_dns 192.168.100.10 "DNS server"
check srv_web 192.168.100.11 "Web server"
check srv_db  192.168.100.12 "Database — access restricted by firewall"

# ── Polo 1 clients ─────────────────────────────────────────────
echo ""
echo "  ┌─ Branch 1 Clients — net_polo1 (192.168.100.64/26) ──┐"
echo "  │  Gateway: 192.168.100.65 (r2_br1 eth0)               │"
echo "  └──────────────────────────────────────────────────────┘"
check pc1_br1 192.168.100.66 "client PC 1"
check pc2_br1 192.168.100.67 "client PC 2"
check pc3_br1 192.168.100.68 "client PC 3"

# ── Polo 2 clients ─────────────────────────────────────────────
echo ""
echo "  ┌─ Branch 2 Clients — net_polo2 (192.168.100.128/26) ─┐"
echo "  │  Gateway: 192.168.100.129 (r3_br2 eth0)              │"
echo "  └──────────────────────────────────────────────────────┘"
check pc1_br2 192.168.100.130 "client PC 1"
check pc2_br2 192.168.100.131 "client PC 2"
check pc3_br2 192.168.100.132 "client PC 3"

# ── Management ─────────────────────────────────────────────────
echo ""
echo "  ┌─ Management — net_gerencia (192.168.100.192/26) ─────┐"
echo "  │  Gateway: 192.168.100.193 (r1_hq eth0)               │"
echo "  └──────────────────────────────────────────────────────┘"
check admin_pc 192.168.100.194 "admin workstation"

# ── Internet ───────────────────────────────────────────────────
echo ""
echo "  ┌─ Internet Devices — net_internet (203.0.113.0/24) ───┐"
echo "  │  Gateway: 203.0.113.1 (r4_edge eth0)                 │"
echo "  └──────────────────────────────────────────────────────┘"
check srv_public_web 203.0.113.10 "public web server (NAT test target)"
check ext_client     203.0.113.20 "external client (simulated attacker)"

# ── Kernel routing tables ──────────────────────────────────────
echo ""
echo "  ┌─ Kernel Routing Tables ──────────────────────────────┐"
echo "  │  Assigning an IP automatically creates a connected   │"
echo "  │  route in the kernel for that subnet. These confirm  │"
echo "  │  the IP and mask are correct on each host.           │"
echo "  └──────────────────────────────────────────────────────┘"

for host in srv_dns srv_web srv_db pc1_br1 pc2_br1 pc3_br1 pc1_br2 pc2_br2 pc3_br2 admin_pc srv_public_web ext_client; do
    echo ""
    echo "  [$host] ip route:"
    docker exec "$host" ip route | sed 's/^/    /'
done

echo ""
echo "============================================================"
if [ "$FAIL" -eq 0 ]; then
    echo "  ALL $PASS checks PASSED"
    echo "  All hosts are correctly configured."
    echo "  Next: bash scripts/03_routing/run.sh"
else
    echo "  $PASS passed | $FAIL FAILED"
    echo "  Fix the issues above before continuing."
fi
echo "============================================================"
