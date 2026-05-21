#!/bin/bash
# =============================================================
# 03_routing/run.sh — Configure static routes
#
# After IP assignment, each device only knows its own subnet.
# This step teaches every device where to forward traffic
# destined outside its local subnet.
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
echo "  STEP 3 — Static Routing"
echo "============================================================"
echo "  Devices only know their own subnet after IP assignment."
echo "  This step teaches every device where to forward traffic"
echo "  that is destined outside its local subnet."
echo "============================================================"

echo ""
echo "  ┌─ Router Routes ──────────────────────────────────────┐"
echo "  │  Routers share net_servico, so they can use each     │"
echo "  │  other as next-hops directly (no extra hops needed). │"
echo "  └──────────────────────────────────────────────────────┘"

# ── r1_hq ─────────────────────────────────────────────────────
echo ""
echo "  [r1_hq] already knows: net_gerencia (.192/26), net_servico (.0/26)"
echo ""

run_cmd "r1_hq needs to forward Polo 1 traffic — sends it to r2_br1 as next-hop on net_servico" \
    docker exec r1_hq ip route add 192.168.100.64/26 via 192.168.100.2

run_cmd "r1_hq needs to forward Polo 2 traffic — sends it to r3_br2 as next-hop on net_servico" \
    docker exec r1_hq ip route add 192.168.100.128/26 via 192.168.100.3

run_cmd "r1_hq needs a path to the internet — any unknown destination goes to r4_edge" \
    docker exec r1_hq ip route add default via 192.168.100.4

# ── r2_br1 ────────────────────────────────────────────────────
echo "  [r2_br1] already knows: net_polo1 (.64/26), net_servico (.0/26)"
echo ""

run_cmd "r2_br1 needs to forward Polo 2 traffic — sends it to r3_br2 as next-hop on net_servico" \
    docker exec r2_br1 ip route add 192.168.100.128/26 via 192.168.100.3

run_cmd "r2_br1 needs to forward management traffic — sends it to r1_hq as next-hop on net_servico" \
    docker exec r2_br1 ip route add 192.168.100.192/26 via 192.168.100.1

run_cmd "r2_br1 needs a path to the internet — any unknown destination goes to r4_edge" \
    docker exec r2_br1 ip route add default via 192.168.100.4

# ── r3_br2 ────────────────────────────────────────────────────
echo "  [r3_br2] already knows: net_polo2 (.128/26), net_servico (.0/26)"
echo ""

run_cmd "r3_br2 needs to forward Polo 1 traffic — sends it to r2_br1 as next-hop on net_servico" \
    docker exec r3_br2 ip route add 192.168.100.64/26 via 192.168.100.2

run_cmd "r3_br2 needs to forward management traffic — sends it to r1_hq as next-hop on net_servico" \
    docker exec r3_br2 ip route add 192.168.100.192/26 via 192.168.100.1

run_cmd "r3_br2 needs a path to the internet — any unknown destination goes to r4_edge" \
    docker exec r3_br2 ip route add default via 192.168.100.4

# ── r4_edge ───────────────────────────────────────────────────
echo "  [r4_edge] already knows: net_internet (203.0.113.0/24), net_servico (.0/26)"
echo "            No default needed — r4_edge IS the internet gateway"
echo ""

run_cmd "r4_edge needs this so NAT reply packets can find their way back to Polo 1 hosts" \
    docker exec r4_edge ip route add 192.168.100.64/26 via 192.168.100.2

run_cmd "r4_edge needs this so NAT reply packets can find their way back to Polo 2 hosts" \
    docker exec r4_edge ip route add 192.168.100.128/26 via 192.168.100.3

run_cmd "r4_edge needs this so NAT reply packets can find their way back to management hosts" \
    docker exec r4_edge ip route add 192.168.100.192/26 via 192.168.100.1

# ── END HOSTS ─────────────────────────────────────────────────
echo ""
echo "  ┌─ Host Default Gateways ──────────────────────────────┐"
echo "  │  Each host sends unknown traffic to its local router. │"
echo "  │  The router then handles forwarding from there.       │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""

echo "  [net_servico servers — default via r4_edge (192.168.100.4)]"
echo ""
run_cmd "srv_dns has no route to the internet yet — this adds it via r4_edge" \
    docker exec srv_dns ip route add default via 192.168.100.4
run_cmd "srv_web has no route to the internet yet — this adds it via r4_edge" \
    docker exec srv_web ip route add default via 192.168.100.4
run_cmd "srv_db has no route to the internet yet — this adds it via r4_edge" \
    docker exec srv_db ip route add default via 192.168.100.4

echo "  [net_polo1 clients — default via r2_br1 (192.168.100.65)]"
echo ""
run_cmd "pc1_br1 only knows net_polo1 — this teaches it to send everything else to r2_br1" \
    docker exec pc1_br1 ip route add default via 192.168.100.65
run_cmd "pc2_br1 only knows net_polo1 — this teaches it to send everything else to r2_br1" \
    docker exec pc2_br1 ip route add default via 192.168.100.65
run_cmd "pc3_br1 only knows net_polo1 — this teaches it to send everything else to r2_br1" \
    docker exec pc3_br1 ip route add default via 192.168.100.65

echo "  [net_polo2 clients — default via r3_br2 (192.168.100.129)]"
echo ""
run_cmd "pc1_br2 only knows net_polo2 — this teaches it to send everything else to r3_br2" \
    docker exec pc1_br2 ip route add default via 192.168.100.129
run_cmd "pc2_br2 only knows net_polo2 — this teaches it to send everything else to r3_br2" \
    docker exec pc2_br2 ip route add default via 192.168.100.129
run_cmd "pc3_br2 only knows net_polo2 — this teaches it to send everything else to r3_br2" \
    docker exec pc3_br2 ip route add default via 192.168.100.129

echo "  [net_gerencia — default via r1_hq (192.168.100.193)]"
echo ""
run_cmd "admin_pc only knows net_gerencia — this teaches it to send everything else to r1_hq" \
    docker exec admin_pc ip route add default via 192.168.100.193

echo "  [net_internet — default via r4_edge (203.0.113.1)]"
echo ""
run_cmd "srv_public_web needs a return path — sends unknown traffic back via r4_edge" \
    docker exec srv_public_web ip route add default via 203.0.113.1
run_cmd "ext_client needs a return path — sends unknown traffic back via r4_edge" \
    docker exec ext_client ip route add default via 203.0.113.1

echo "============================================================"
echo "  Routing configured."
echo "  Run: bash scripts/03_routing/test.sh   to verify"
echo "============================================================"
