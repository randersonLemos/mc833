#!/bin/bash
# =============================================================
# 01_test_routers.sh — Verify router IP assignment
#
# Two levels of verification:
#
#   1. IP on correct interface
#      We check that each IP is on the specific interface
#      (eth0 or eth1) it was assigned to, not just anywhere.
#      Command: ip addr show <iface> | grep <ip>
#
#   2. Reachability on net_servico (ping)
#      All 4 routers share the backbone (192.168.100.0/26).
#      At this point, they should already be able to reach
#      each other — no routing config needed, they are on
#      the same subnet.
# =============================================================

PASS=0
FAIL=0

check_iface() {
    local container=$1
    local iface=$2
    local expected_ip=$3
    local description=$4

    if docker exec "$container" ip addr show "$iface" 2>/dev/null | grep -q "$expected_ip"; then
        printf "    [PASS] %-10s %-6s → %-20s %s\n" "$container" "$iface" "$expected_ip" "$description"
        PASS=$((PASS + 1))
    else
        printf "    [FAIL] %-10s %-6s → %-20s %s\n" "$container" "$iface" "$expected_ip" "$description"
        FAIL=$((FAIL + 1))
    fi
}

check_ping() {
    local from=$1
    local to_ip=$2
    local to_name=$3

    if docker exec "$from" ping -c1 -W1 "$to_ip" > /dev/null 2>&1; then
        printf "    [PASS] %-10s → %-18s %-14s reachable on net_servico\n" "$from" "$to_ip" "($to_name)"
        PASS=$((PASS + 1))
    else
        printf "    [FAIL] %-10s → %-18s %-14s UNREACHABLE\n" "$from" "$to_ip" "($to_name)"
        FAIL=$((FAIL + 1))
    fi
}

echo ""
echo "============================================================"
echo "  TEST 1 — Router IP Assignment Verification"
echo "============================================================"

# ── Level 1: IP on the correct interface ─────────────────────
echo ""
echo "  ┌─ Level 1 — IP on the correct interface ──────────────┐"
echo "  │  Checks that each IP is bound to the right           │"
echo "  │  interface (eth0 or eth1), not just anywhere.        │"
echo "  └──────────────────────────────────────────────────────┘"

echo ""
echo "  [r1_hq] bridges net_gerencia (.192/26) ↔ net_servico (.0/26)"
check_iface r1_hq eth0 192.168.100.193 "net_gerencia — gateway for admin_pc"
check_iface r1_hq eth1 192.168.100.1   "net_servico  — backbone identity"

echo ""
echo "  [r2_br1] bridges net_polo1 (.64/26) ↔ net_servico (.0/26)"
check_iface r2_br1 eth0 192.168.100.65 "net_polo1   — gateway for pc1/2/3_br1"
check_iface r2_br1 eth1 192.168.100.2  "net_servico — backbone identity"

echo ""
echo "  [r3_br2] bridges net_polo2 (.128/26) ↔ net_servico (.0/26)"
check_iface r3_br2 eth0 192.168.100.129 "net_polo2   — gateway for pc1/2/3_br2"
check_iface r3_br2 eth1 192.168.100.3   "net_servico — backbone identity"

echo ""
echo "  [r4_edge] bridges net_internet (203.0.113.0/24) ↔ net_servico (.0/26)"
check_iface r4_edge eth0 203.0.113.1   "net_internet — public-facing, will do NAT"
check_iface r4_edge eth1 192.168.100.4 "net_servico  — backbone identity"

# ── Level 2: Routers can reach each other on net_servico ─────
echo ""
echo "  ┌─ Level 2 — Reachability on net_servico ──────────────┐"
echo "  │  All routers share 192.168.100.0/26 via eth1.        │"
echo "  │  No routing config is needed yet — they are on the   │"
echo "  │  same subnet, so ping must work directly.            │"
echo "  │  A failure here means the IP or mask is wrong.       │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""

check_ping r1_hq   192.168.100.2 "r2_br1"
check_ping r1_hq   192.168.100.3 "r3_br2"
check_ping r1_hq   192.168.100.4 "r4_edge"

check_ping r2_br1  192.168.100.1 "r1_hq"
check_ping r2_br1  192.168.100.3 "r3_br2"
check_ping r2_br1  192.168.100.4 "r4_edge"

check_ping r3_br2  192.168.100.1 "r1_hq"
check_ping r3_br2  192.168.100.2 "r2_br1"
check_ping r3_br2  192.168.100.4 "r4_edge"

check_ping r4_edge 192.168.100.1 "r1_hq"
check_ping r4_edge 192.168.100.2 "r2_br1"
check_ping r4_edge 192.168.100.3 "r3_br2"

echo ""
echo "  ┌─ Level 3 — Kernel Routing Tables ────────────────────┐"
echo "  │  When an IP is assigned to an interface, the kernel  │"
echo "  │  automatically creates a route for that subnet.      │"
echo "  │  These are the connected routes — no static config   │"
echo "  │  needed. They confirm the IP and mask are correct.   │"
echo "  └──────────────────────────────────────────────────────┘"

for router in r1_hq r2_br1 r3_br2 r4_edge; do
    echo ""
    echo "  [$router] ip route:"
    docker exec "$router" ip route | sed 's/^/    /'
done

echo ""
echo "============================================================"
if [ "$FAIL" -eq 0 ]; then
    echo "  ALL $PASS checks PASSED"
    echo "  Routers are correctly configured."
    echo "  Next: bash scripts/02_assign_hosts.sh"
else
    echo "  $PASS passed | $FAIL FAILED"
    echo "  Fix the issues above before continuing."
fi
echo "============================================================"
