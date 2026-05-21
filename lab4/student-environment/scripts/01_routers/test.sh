#!/bin/bash
# =============================================================
# 01_routers/test.sh — Verify router IP assignment
# =============================================================

PASS=0
FAIL=0

check_iface() {
    local container=$1
    local iface=$2
    local expected_ip=$3
    local description=$4

    printf "    Reason  : Confirm %s is bound to %s on %s\n" "$expected_ip" "$iface" "$container"
    printf "    Command : docker exec %s ip addr show %s | grep %s\n" "$container" "$iface" "$expected_ip"
    local output
    output=$(docker exec "$container" ip addr show "$iface" 2>/dev/null | grep "$expected_ip")
    if [ -n "$output" ]; then
        echo "$output" | sed 's/^/    Output  : /'
        printf "    Status  : [PASS] %s %s has %s — %s\n\n" "$container" "$iface" "$expected_ip" "$description"
        PASS=$((PASS + 1))
    else
        printf "    Output  : (not found)\n"
        printf "    Status  : [FAIL] %s %s is MISSING %s — %s\n\n" "$container" "$iface" "$expected_ip" "$description"
        FAIL=$((FAIL + 1))
    fi
}

check_ping() {
    local from=$1
    local to_ip=$2
    local to_name=$3

    printf "    Reason  : Routers on the same subnet must reach each other without any routing config\n"
    printf "    Command : docker exec %s ping -c1 -W1 %s\n" "$from" "$to_ip"
    local output
    output=$(docker exec "$from" ping -c1 -W1 "$to_ip" 2>&1)
    local exit_code=$?
    local summary
    summary=$(echo "$output" | grep -E "packets transmitted" | head -1)
    printf "    Output  : %s\n" "$summary"
    if [ "$exit_code" -eq 0 ]; then
        printf "    Status  : [PASS] %s → %s (%s) reachable\n\n" "$from" "$to_ip" "$to_name"
        PASS=$((PASS + 1))
    else
        printf "    Status  : [FAIL] %s → %s (%s) UNREACHABLE\n\n" "$from" "$to_ip" "$to_name"
        FAIL=$((FAIL + 1))
    fi
}

show_routes() {
    local device=$1
    printf "    Reason  : Confirm kernel auto-created connected routes after IP assignment\n"
    printf "    Command : docker exec %s ip route\n" "$device"
    local output
    output=$(docker exec "$device" ip route 2>&1)
    echo "$output" | sed 's/^/    Output  : /'
    printf "    Status  : displayed\n\n"
}

echo ""
echo "============================================================"
echo "  TEST 1 — Router IP Assignment Verification"
echo "============================================================"

# ── Level 1: IP on the correct interface ─────────────────────
echo ""
echo "  ┌─ Level 1 — IP on the correct interface ──────────────┐"
echo "  │  Checks that each IP is bound to the right interface. │"
echo "  └──────────────────────────────────────────────────────┘"

echo ""
echo "  [r1_hq] bridges net_gerencia (.192/26) ↔ net_servico (.0/26)"
check_iface r1_hq eth0 192.168.100.193 "net_gerencia — gateway for admin_pc"
check_iface r1_hq eth1 192.168.100.1   "net_servico  — backbone identity"

echo "  [r2_br1] bridges net_polo1 (.64/26) ↔ net_servico (.0/26)"
check_iface r2_br1 eth0 192.168.100.65 "net_polo1   — gateway for pc1/2/3_br1"
check_iface r2_br1 eth1 192.168.100.2  "net_servico — backbone identity"

echo "  [r3_br2] bridges net_polo2 (.128/26) ↔ net_servico (.0/26)"
check_iface r3_br2 eth0 192.168.100.129 "net_polo2   — gateway for pc1/2/3_br2"
check_iface r3_br2 eth1 192.168.100.3   "net_servico — backbone identity"

echo "  [r4_edge] bridges net_internet (203.0.113.0/24) ↔ net_servico (.0/26)"
check_iface r4_edge eth0 203.0.113.1   "net_internet — public-facing, will do NAT"
check_iface r4_edge eth1 192.168.100.4 "net_servico  — backbone identity"

# ── Level 2: Routers can reach each other on net_servico ─────
echo ""
echo "  ┌─ Level 2 — Reachability on net_servico ──────────────┐"
echo "  │  All routers share 192.168.100.0/26 via eth1.        │"
echo "  │  No routing config needed — same subnet = direct.    │"
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

# ── Level 3: Kernel routing tables ───────────────────────────
echo ""
echo "  ┌─ Level 3 — Kernel Routing Tables ────────────────────┐"
echo "  │  Assigning an IP auto-creates a connected route in   │"
echo "  │  the kernel. No static config yet.                   │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""

for router in r1_hq r2_br1 r3_br2 r4_edge; do
    echo "  [$router]"
    show_routes "$router"
done

echo "============================================================"
if [ "$FAIL" -eq 0 ]; then
    echo "  ALL $PASS checks PASSED"
    echo "  Routers are correctly configured."
    echo "  Next: bash scripts/02_hosts/run.sh"
else
    echo "  $PASS passed | $FAIL FAILED"
    echo "  Fix the issues above before continuing."
fi
echo "============================================================"
