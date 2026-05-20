#!/bin/bash
# =============================================================
# 03_routing/test.sh — Verify static routing
#
# Three levels of verification:
#
#   1. Routing tables — print ip route for every device to
#      confirm default gateways and static routes are present.
#
#   2. Cross-subnet ping — verify packets actually travel
#      across subnet boundaries through the routers.
#      (Firewall is not applied yet, so all pings should pass.)
#
#   3. Path trace — traceroute from a polo PC to a server to
#      show the exact hops a packet takes.
# =============================================================

PASS=0
FAIL=0

check_ping() {
    local from=$1
    local to_ip=$2
    local to_name=$3
    local description=$4

    if docker exec "$from" ping -c1 -W2 "$to_ip" > /dev/null 2>&1; then
        printf "    [PASS] %-12s → %-18s %-16s %s\n" "$from" "$to_ip" "($to_name)" "$description"
        PASS=$((PASS + 1))
    else
        printf "    [FAIL] %-12s → %-18s %-16s %s\n" "$from" "$to_ip" "($to_name)" "$description"
        FAIL=$((FAIL + 1))
    fi
}

echo ""
echo "============================================================"
echo "  TEST 3 — Static Routing Verification"
echo "============================================================"

# ── Level 1: Routing tables ───────────────────────────────────
echo ""
echo "  ┌─ Level 1 — Routing Tables ───────────────────────────┐"
echo "  │  Shows the full routing table for every device.      │"
echo "  │  Each device should now have a default route in      │"
echo "  │  addition to the kernel connected route.             │"
echo "  └──────────────────────────────────────────────────────┘"

echo ""
echo "  [Routers]"
for router in r1_hq r2_br1 r3_br2 r4_edge; do
    echo ""
    echo "  [$router]"
    docker exec "$router" ip route | sed 's/^/    /'
done

echo ""
echo "  [Corporate Servers]"
for host in srv_dns srv_web srv_db; do
    echo ""
    echo "  [$host]"
    docker exec "$host" ip route | sed 's/^/    /'
done

echo ""
echo "  [Polo 1 Clients]"
for host in pc1_br1 pc2_br1 pc3_br1; do
    echo ""
    echo "  [$host]"
    docker exec "$host" ip route | sed 's/^/    /'
done

echo ""
echo "  [Polo 2 Clients]"
for host in pc1_br2 pc2_br2 pc3_br2; do
    echo ""
    echo "  [$host]"
    docker exec "$host" ip route | sed 's/^/    /'
done

echo ""
echo "  [Management]"
echo ""
echo "  [admin_pc]"
docker exec admin_pc ip route | sed 's/^/    /'

echo ""
echo "  [Internet Devices]"
for host in srv_public_web ext_client; do
    echo ""
    echo "  [$host]"
    docker exec "$host" ip route | sed 's/^/    /'
done

# ── Level 2: Cross-subnet ping ────────────────────────────────
echo ""
echo "  ┌─ Level 2 — Cross-Subnet Reachability ────────────────┐"
echo "  │  Packets must travel through routers to reach these  │"
echo "  │  destinations. Firewall is not applied yet, so all   │"
echo "  │  pings should succeed.                               │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""

echo "  [Polo 1 → Servers]"
check_ping pc1_br1 192.168.100.10 "srv_dns" "DNS server on net_servico"
check_ping pc1_br1 192.168.100.11 "srv_web" "Web server on net_servico"
check_ping pc1_br1 192.168.100.12 "srv_db"  "DB server on net_servico"

echo ""
echo "  [Polo 2 → Servers]"
check_ping pc1_br2 192.168.100.10 "srv_dns" "DNS server on net_servico"
check_ping pc1_br2 192.168.100.11 "srv_web" "Web server on net_servico"
check_ping pc1_br2 192.168.100.12 "srv_db"  "DB server on net_servico"

echo ""
echo "  [Polo 1 ↔ Polo 2]"
check_ping pc1_br1 192.168.100.130 "pc1_br2" "cross-branch (will be BLOCKED after firewall)"
check_ping pc1_br2 192.168.100.66  "pc1_br1" "cross-branch (will be BLOCKED after firewall)"

echo ""
echo "  [Polos → Management]"
check_ping pc1_br1 192.168.100.194 "admin_pc" "management (will be BLOCKED after firewall)"
check_ping pc1_br2 192.168.100.194 "admin_pc" "management (will be BLOCKED after firewall)"

# ── Level 3: Traceroute ───────────────────────────────────────
echo ""
echo "  ┌─ Level 3 — Packet Path Trace ────────────────────────┐"
echo "  │  Shows every router hop a packet takes from           │"
echo "  │  pc1_br1 to srv_dns. Confirms traffic flows through   │"
echo "  │  r2_br1 (the gateway) before reaching the server.    │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""
echo "  traceroute: pc1_br1 → srv_dns (192.168.100.10)"
echo ""
docker exec pc1_br1 traceroute -n -w1 192.168.100.10 | sed 's/^/    /'

echo ""
echo "============================================================"
if [ "$FAIL" -eq 0 ]; then
    echo "  ALL $PASS checks PASSED"
    echo "  Routing is working correctly."
    echo "  Next: bash scripts/04_nat/run.sh"
else
    echo "  $PASS passed | $FAIL FAILED"
    echo "  Fix the issues above before continuing."
fi
echo "============================================================"
