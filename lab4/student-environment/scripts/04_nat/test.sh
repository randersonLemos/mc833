#!/bin/bash
# =============================================================
# 04_nat/test.sh — Verify NAT is working
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
        printf "    Status  : [PASS] %s → %s (%s) reachable\n\n" "$from" "$to_ip" "$to_name"
        PASS=$((PASS + 1))
    else
        printf "    Status  : [FAIL] %s → %s (%s) UNREACHABLE\n\n" "$from" "$to_ip" "$to_name"
        FAIL=$((FAIL + 1))
    fi
}

echo ""
echo "============================================================"
echo "  TEST 4 — NAT Verification"
echo "============================================================"

# ── Level 1: NAT rule present ─────────────────────────────────
echo ""
echo "  ┌─ Level 1 — NAT Rule on r4_edge ──────────────────────┐"
echo "  │  Confirms the MASQUERADE rule exists in the NAT table │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""

printf "    Reason  : Inspect the full NAT POSTROUTING chain on r4_edge\n"
printf "    Command : docker exec r4_edge iptables -t nat -L POSTROUTING -v\n"
nat_output=$(docker exec r4_edge iptables -t nat -L POSTROUTING -v 2>&1)
echo "$nat_output" | sed 's/^/    Output  : /'
printf "    Status  : displayed\n\n"

printf "    Reason  : Confirm MASQUERADE keyword is present in the NAT table\n"
printf "    Command : docker exec r4_edge iptables -t nat -L POSTROUTING | grep MASQUERADE\n"
grep_output=$(docker exec r4_edge iptables -t nat -L POSTROUTING 2>&1 | grep "MASQUERADE")
if [ -n "$grep_output" ]; then
    echo "$grep_output" | sed 's/^/    Output  : /'
    printf "    Status  : [PASS] MASQUERADE rule is present on r4_edge\n\n"
    PASS=$((PASS + 1))
else
    printf "    Output  : (not found)\n"
    printf "    Status  : [FAIL] MASQUERADE rule MISSING — run 04_nat/run.sh first\n\n"
    FAIL=$((FAIL + 1))
fi

# ── Level 2: Internal hosts can reach internet ────────────────
echo ""
echo "  ┌─ Level 2 — Internet Reachability via NAT ────────────┐"
echo "  │  Packet leaves as 192.168.100.x, arrives as          │"
echo "  │  203.0.113.1. A timeout means NAT is not working.    │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""

echo "  [Polo 1 → Internet]"
check_ping pc1_br1 203.0.113.10 "srv_public_web" "pc1_br1 reaches internet via r2_br1 → r4_edge NAT"
check_ping pc2_br1 203.0.113.10 "srv_public_web" "pc2_br1 reaches internet via r2_br1 → r4_edge NAT"
check_ping pc3_br1 203.0.113.10 "srv_public_web" "pc3_br1 reaches internet via r2_br1 → r4_edge NAT"

echo "  [Polo 2 → Internet]"
check_ping pc1_br2 203.0.113.10 "srv_public_web" "pc1_br2 reaches internet via r3_br2 → r4_edge NAT"
check_ping pc2_br2 203.0.113.10 "srv_public_web" "pc2_br2 reaches internet via r3_br2 → r4_edge NAT"
check_ping pc3_br2 203.0.113.10 "srv_public_web" "pc3_br2 reaches internet via r3_br2 → r4_edge NAT"

echo "  [Management → Internet]"
check_ping admin_pc 203.0.113.10 "srv_public_web" "admin_pc reaches internet via r1_hq → r4_edge NAT"

# ── Level 3: Traceroute ───────────────────────────────────────
echo ""
echo "  ┌─ Level 3 — Packet Path to Internet ──────────────────┐"
echo "  │  Expected: pc1_br1 → r2_br1 (.65) → r4_edge → web   │"
echo "  │  After r4_edge the source IP becomes 203.0.113.1     │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""
printf "    Reason  : Trace the full path and observe NAT translation at r4_edge\n"
printf "    Command : docker exec pc1_br1 traceroute -n -w1 203.0.113.10\n"
trace_output=$(docker exec pc1_br1 traceroute -n -w1 203.0.113.10 2>&1)
echo "$trace_output" | sed 's/^/    Output  : /'
printf "    Status  : displayed\n"

echo ""
echo "============================================================"
if [ "$FAIL" -eq 0 ]; then
    echo "  ALL $PASS checks PASSED"
    echo "  NAT is working correctly."
    echo "  Next: bash scripts/05_firewall/run.sh"
else
    echo "  $PASS passed | $FAIL FAILED"
    echo "  Fix the issues above before continuing."
fi
echo "============================================================"
