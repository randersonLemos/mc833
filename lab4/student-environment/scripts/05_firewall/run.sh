#!/bin/bash
# =============================================================
# 05_firewall/run.sh — Apply iptables firewall rules
#
# Rules are applied to the FORWARD chain of each router.
# The FORWARD chain handles packets that PASS THROUGH a router
# (not destined to the router itself).
#
# Rule order matters — iptables processes top to bottom and
# stops at the first match. ESTABLISHED,RELATED always comes
# first so replies are never caught by a DROP rule below.
# =============================================================

run_cmd() {
    local reason="$1"
    shift
    printf "    Reason  : %s\n" "$reason"
    printf "    Command : %s\n" "$*"
    local output
    output=$("$@" 2>&1)
    local exit_code=$?
    if [ -n "$output" ]; then
        echo "$output" | sed 's/^/    Output  : /'
    else
        printf "    Output  : (no output)\n"
    fi
    if [ "$exit_code" -eq 0 ]; then
        printf "    Status  : done (exit 0)\n\n"
    else
        printf "    Status  : FAILED (exit %d)\n\n" "$exit_code"
    fi
    return $exit_code
}

echo ""
echo "============================================================"
echo "  STEP 5 — Firewall Rules"
echo "============================================================"
echo "  Rules go into the FORWARD chain — packets passing through"
echo "  the router, not destined to it."
echo "  ESTABLISHED,RELATED is always rule #1 so that replies to"
echo "  open connections are never accidentally dropped."
echo "============================================================"

# ── r2_br1 — Polo 1 gateway ───────────────────────────────────
echo ""
echo "  ┌─ [r2_br1] Polo 1 Gateway ────────────────────────────┐"
echo "  │  All outbound traffic from Polo 1 exits here first.  │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""

run_cmd "Rule #1 — must be first: allow reply packets for connections Polo 1 already opened (stateful)" \
    docker exec r2_br1 iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT

run_cmd "Rule #2 — block Polo 1 → Polo 2: bidirectional isolation requirement" \
    docker exec r2_br1 iptables -A FORWARD -s 192.168.100.64/26 -d 192.168.100.128/26 -j DROP

run_cmd "Rule #3 — block Polo 1 → srv_db: database must not be reachable from branches" \
    docker exec r2_br1 iptables -A FORWARD -s 192.168.100.64/26 -d 192.168.100.12 -j DROP

run_cmd "Rule #4 — block Polo 1 → net_gerencia: management network must be isolated from branches" \
    docker exec r2_br1 iptables -A FORWARD -s 192.168.100.64/26 -d 192.168.100.192/26 -j DROP

# ── r3_br2 — Polo 2 gateway ───────────────────────────────────
echo ""
echo "  ┌─ [r3_br2] Polo 2 Gateway ────────────────────────────┐"
echo "  │  All outbound traffic from Polo 2 exits here first.  │"
echo "  │  Mirror of r2_br1 rules for Polo 2 source range.     │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""

run_cmd "Rule #1 — must be first: allow reply packets for connections Polo 2 already opened (stateful)" \
    docker exec r3_br2 iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT

run_cmd "Rule #2 — block Polo 2 → Polo 1: bidirectional isolation requirement" \
    docker exec r3_br2 iptables -A FORWARD -s 192.168.100.128/26 -d 192.168.100.64/26 -j DROP

run_cmd "Rule #3 — block Polo 2 → srv_db: database must not be reachable from branches" \
    docker exec r3_br2 iptables -A FORWARD -s 192.168.100.128/26 -d 192.168.100.12 -j DROP

run_cmd "Rule #4 — block Polo 2 → net_gerencia: management network must be isolated from branches" \
    docker exec r3_br2 iptables -A FORWARD -s 192.168.100.128/26 -d 192.168.100.192/26 -j DROP

# ── r1_hq — Gerencia gateway ──────────────────────────────────
echo ""
echo "  ┌─ [r1_hq] Management Gateway ─────────────────────────┐"
echo "  │  All traffic leaving net_gerencia exits here.        │"
echo "  │  Blocks admin from reaching branches and database.   │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""

run_cmd "Rule #1 — must be first: allow reply packets for connections admin already opened (stateful)" \
    docker exec r1_hq iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT

run_cmd "Rule #2 — block gerencia → Polo 1: management must not access branch clients" \
    docker exec r1_hq iptables -A FORWARD -s 192.168.100.192/26 -d 192.168.100.64/26 -j DROP

run_cmd "Rule #3 — block gerencia → Polo 2: management must not access branch clients" \
    docker exec r1_hq iptables -A FORWARD -s 192.168.100.192/26 -d 192.168.100.128/26 -j DROP

run_cmd "Rule #4 — block gerencia → srv_db: database must not be reachable from management either" \
    docker exec r1_hq iptables -A FORWARD -s 192.168.100.192/26 -d 192.168.100.12 -j DROP

# ── r4_edge — Stateful internet firewall ──────────────────────
echo ""
echo "  ┌─ [r4_edge] Stateful Internet Firewall ───────────────┐"
echo "  │  Blocks internet from initiating connections inward. │"
echo "  │  Internal hosts can still reach the internet — their │"
echo "  │  replies come back in via ESTABLISHED,RELATED.       │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""

run_cmd "Rule #1 — must be first: allow replies to connections that internal hosts already opened" \
    docker exec r4_edge iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT

run_cmd "Rule #2 — block internet → internal: drop any NEW connection arriving from eth0 (internet side)" \
    docker exec r4_edge iptables -A FORWARD -i eth0 -m state --state NEW -j DROP

echo "============================================================"
echo "  Firewall rules applied."
echo "  Run: bash scripts/05_firewall/test.sh   to verify"
echo "============================================================"
