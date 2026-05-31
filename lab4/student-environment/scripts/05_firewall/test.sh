#!/bin/bash
# =============================================================
# 05_firewall/test.sh — Verify all firewall rules
# =============================================================

PASS=0
FAIL=0

expect_pass() {
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
        printf "    Status  : [PASS] %s → %s (%s) reachable as expected\n\n" "$from" "$to_ip" "$to_name"
        PASS=$((PASS + 1))
    else
        printf "    Status  : [FAIL] %s → %s (%s) UNREACHABLE — should be allowed\n\n" "$from" "$to_ip" "$to_name"
        FAIL=$((FAIL + 1))
    fi
}

expect_block() {
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
        printf "    Status  : [FAIL] %s → %s (%s) reachable — should be BLOCKED\n\n" "$from" "$to_ip" "$to_name"
        FAIL=$((FAIL + 1))
    else
        printf "    Status  : [PASS] %s → %s (%s) blocked as expected\n\n" "$from" "$to_ip" "$to_name"
        PASS=$((PASS + 1))
    fi
}

echo ""
echo "============================================================"
echo "  TEST 5 — Firewall Verification"
echo "============================================================"

# ── Active rules dump ─────────────────────────────────────────
echo ""
echo "  ┌─ Active FORWARD Rules ────────────────────────────────┐"
echo "  │  Shows all iptables rules currently on each router.  │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""

for router in r1_hq r2_br1 r3_br2 r4_edge; do
    printf "    Reason  : Inspect all FORWARD rules on %s\n" "$router"
    printf "    Command : docker exec %s iptables -L FORWARD -v\n" "$router"
    fw_output=$(docker exec "$router" iptables -L FORWARD -v 2>&1)
    echo "$fw_output" | sed 's/^/    Output  : /'
    printf "    Status  : displayed\n\n"
done

# ── Must PASS ─────────────────────────────────────────────────
echo ""
echo "  ┌─ Connectivity — Must PASS ────────────────────────────┐"
echo "  │  These connections must still work after the firewall. │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""

echo "  [Polo 1 → Allowed destinations]"
expect_pass pc1_br1 192.168.100.11 "srv_web" "Polo 1 must reach web server"
expect_pass pc1_br1 203.0.113.10   "srv_pub" "Polo 1 must reach internet via NAT"

echo "  [Polo 2 → Allowed destinations]"
expect_pass pc1_br2 192.168.100.11 "srv_web" "Polo 2 must reach web server"
expect_pass pc1_br2 203.0.113.10   "srv_pub" "Polo 2 must reach internet via NAT"

# ── Must BLOCK ────────────────────────────────────────────────
echo ""
echo "  ┌─ Isolation — Must BLOCK ──────────────────────────────┐"
echo "  │  These connections must be dropped by the firewall.   │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""

echo "  [Polo 1 ↔ Polo 2 — bidirectional block]"
expect_block pc1_br1 192.168.100.130 "pc1_br2" "r2_br1 drops src=polo1 dst=polo2"
expect_block pc1_br2 192.168.100.66  "pc1_br1" "r3_br2 drops src=polo2 dst=polo1"

echo "  [Polos → srv_db]"
expect_block pc1_br1 192.168.100.12 "srv_db" "r2_br1 drops src=polo1 dst=srv_db"
expect_block pc1_br2 192.168.100.12 "srv_db" "r3_br2 drops src=polo2 dst=srv_db"

echo "  [Polos → srv_dns]"
expect_block pc1_br1 192.168.100.10 "srv_dns" "r2_br1 drops src=polo1 dst=srv_dns"
expect_block pc1_br2 192.168.100.10 "srv_dns" "r3_br2 drops src=polo2 dst=srv_dns"

echo "  [Polos → net_gerencia]"
expect_block pc1_br1 192.168.100.194 "admin_pc" "r2_br1 drops src=polo1 dst=gerencia"
expect_block pc1_br2 192.168.100.194 "admin_pc" "r3_br2 drops src=polo2 dst=gerencia"

echo "  [gerencia → Polos]"
expect_block admin_pc 192.168.100.66  "pc1_br1" "r1_hq drops src=gerencia dst=polo1"
expect_block admin_pc 192.168.100.130 "pc1_br2" "r1_hq drops src=gerencia dst=polo2"

echo "  [gerencia → srv_db]"
expect_block admin_pc 192.168.100.12 "srv_db" "r1_hq drops src=gerencia dst=srv_db"

echo "  [gerencia → srv_dns]"
expect_block admin_pc 192.168.100.10 "srv_dns" "r1_hq drops src=gerencia dst=srv_dns"

echo "  [Internet → internal (stateful)]"
expect_block ext_client 192.168.100.66  "pc1_br1" "r4_edge drops NEW connection from eth0 to Polo 1"
expect_block ext_client 192.168.100.130 "pc1_br2" "r4_edge drops NEW connection from eth0 to Polo 2"
expect_block ext_client 192.168.100.194 "admin_pc" "r4_edge drops NEW connection from eth0 to management"

echo ""
echo "============================================================"
if [ "$FAIL" -eq 0 ]; then
    echo "  ALL $PASS checks PASSED"
    echo "  Security policy is correctly enforced."
else
    echo "  $PASS passed | $FAIL FAILED"
    echo "  Fix the issues above before submitting."
fi
echo "============================================================"
