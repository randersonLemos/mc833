#!/bin/bash
# =============================================================
# 03_routing/test.sh — Verify static routing
# =============================================================

PASS=0
FAIL=0

check_ping() {
    local from=$1
    local to_ip=$2
    local to_name=$3
    local description=$4

    printf "    Reason  : %s\n" "$description"
    printf "    Command : docker exec %s ping -c1 -W2 %s\n" "$from" "$to_ip"
    local output
    output=$(docker exec "$from" ping -c1 -W2 "$to_ip" 2>&1)
    local exit_code=$?
    local summary
    summary=$(echo "$output" | grep -E "packets transmitted" | head -1)
    printf "    Output  : %s\n" "$summary"
    if [ "$exit_code" -eq 0 ]; then
        printf "    Status  : [PASS] %s → %s (%s)\n\n" "$from" "$to_ip" "$to_name"
        PASS=$((PASS + 1))
    else
        printf "    Status  : [FAIL] %s → %s (%s)\n\n" "$from" "$to_ip" "$to_name"
        FAIL=$((FAIL + 1))
    fi
}

show_routes() {
    local device=$1
    printf "    Reason  : Confirm default gateway and static routes are present\n"
    printf "    Command : docker exec %s ip route\n" "$device"
    local output
    output=$(docker exec "$device" ip route 2>&1)
    echo "$output" | sed 's/^/    Output  : /'
    printf "    Status  : displayed\n\n"
}

echo ""
echo "============================================================"
echo "  TEST 3 — Static Routing Verification"
echo "============================================================"

# ── Level 1: Routing tables ───────────────────────────────────
echo ""
echo "  ┌─ Level 1 — Routing Tables ───────────────────────────┐"
echo "  │  Each device should now have a default route in      │"
echo "  │  addition to its kernel connected route.             │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""

for device in r1_hq r2_br1 r3_br2 r4_edge srv_dns srv_web srv_db \
              pc1_br1 pc2_br1 pc3_br1 pc1_br2 pc2_br2 pc3_br2 \
              admin_pc srv_public_web ext_client; do
    echo "  [$device]"
    show_routes "$device"
done

# ── Level 2: Cross-subnet ping ────────────────────────────────
echo ""
echo "  ┌─ Level 2 — Cross-Subnet Reachability ────────────────┐"
echo "  │  Packets must travel through routers to reach these  │"
echo "  │  destinations. Firewall not applied yet — all should │"
echo "  │  pass. Note which ones will be blocked in step 5.    │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""

echo "  [Polo 1 → Servers]"
check_ping pc1_br1 192.168.100.10 "srv_dns" "Polo 1 reaching DNS across subnet via r2_br1"
check_ping pc1_br1 192.168.100.11 "srv_web" "Polo 1 reaching web server across subnet via r2_br1"
check_ping pc1_br1 192.168.100.12 "srv_db"  "Polo 1 reaching DB — will be BLOCKED in step 5"

echo "  [Polo 2 → Servers]"
check_ping pc1_br2 192.168.100.10 "srv_dns" "Polo 2 reaching DNS across subnet via r3_br2"
check_ping pc1_br2 192.168.100.11 "srv_web" "Polo 2 reaching web server across subnet via r3_br2"
check_ping pc1_br2 192.168.100.12 "srv_db"  "Polo 2 reaching DB — will be BLOCKED in step 5"

echo "  [Polo 1 ↔ Polo 2 — will be BLOCKED after firewall]"
check_ping pc1_br1 192.168.100.130 "pc1_br2" "Cross-branch — will be BLOCKED in step 5"
check_ping pc1_br2 192.168.100.66  "pc1_br1" "Cross-branch — will be BLOCKED in step 5"

echo "  [Polos → Management — will be BLOCKED after firewall]"
check_ping pc1_br1 192.168.100.194 "admin_pc" "Polo 1 to management — will be BLOCKED in step 5"
check_ping pc1_br2 192.168.100.194 "admin_pc" "Polo 2 to management — will be BLOCKED in step 5"

# ── Level 3: Traceroute ───────────────────────────────────────
echo ""
echo "  ┌─ Level 3 — Packet Path Trace ────────────────────────┐"
echo "  │  Shows every hop from pc1_br1 to srv_dns.            │"
echo "  │  Expected: pc1_br1 → r2_br1 (.65) → srv_dns (.10)   │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""
printf "    Reason  : Verify the exact routing path pc1_br1 → r2_br1 → srv_dns\n"
printf "    Command : docker exec pc1_br1 traceroute -n -w1 192.168.100.10\n"
local_output=$(docker exec pc1_br1 traceroute -n -w1 192.168.100.10 2>&1)
echo "$local_output" | sed 's/^/    Output  : /'
printf "    Status  : displayed\n"

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
