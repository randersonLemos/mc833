#!/bin/bash
# =============================================================
# 01_routers/run.sh — Assign IPs to routers
#
# Interface mapping (from docker-compose.yml priority field):
#   r1_hq:   eth0=net_gerencia  | eth1=net_servico
#   r2_br1:  eth0=net_polo1     | eth1=net_servico
#   r3_br2:  eth0=net_polo2     | eth1=net_servico
#   r4_edge: eth0=net_internet  | eth1=net_servico
# =============================================================

# Prints the reason and the exact command, then runs it.
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
echo "  STEP 1 — Router IP Assignment"
echo "============================================================"
echo "  Routers are the only devices with two interfaces."
echo "  Each interface connects to a different subnet."
echo "  The IP assigned to each interface becomes the DEFAULT"
echo "  GATEWAY for all devices in that subnet."
echo "============================================================"

# ── r1_hq ─────────────────────────────────────────────────────
echo ""
echo "  ┌─ [r1_hq] Headquarters Router ────────────────────────┐"
echo "  │  Role: connects Management to the backbone           │"
echo "  │  ip_forward=1 allows it to route between both        │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""
echo "  eth0 → net_gerencia | Subnet: 192.168.100.192/26 | Range: .193–.254"
echo ""
run_cmd "Remove Docker's auto-assigned IP from eth0 to avoid duplicate addresses" \
    docker exec r1_hq ip addr flush dev eth0

run_cmd "Assign gateway IP for net_gerencia — admin_pc will use this as its default gateway" \
    docker exec r1_hq ip addr add 192.168.100.193/26 dev eth0

echo "  eth1 → net_servico | Subnet: 192.168.100.0/26 | Range: .1–.62"
echo ""
run_cmd "Remove Docker's auto-assigned IP from eth1 to avoid duplicate addresses" \
    docker exec r1_hq ip addr flush dev eth1

run_cmd "Assign backbone identity of r1_hq — other routers use this IP as next-hop" \
    docker exec r1_hq ip addr add 192.168.100.1/26 dev eth1

# ── r2_br1 ────────────────────────────────────────────────────
echo ""
echo "  ┌─ [r2_br1] Branch 1 Router ───────────────────────────┐"
echo "  │  Role: connects Polo 1 clients to the backbone       │"
echo "  │  ip_forward=1 allows it to route between both        │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""
echo "  eth0 → net_polo1 | Subnet: 192.168.100.64/26 | Range: .65–.126"
echo ""
run_cmd "Remove Docker's auto-assigned IP from eth0 to avoid duplicate addresses" \
    docker exec r2_br1 ip addr flush dev eth0

run_cmd "Assign gateway IP for net_polo1 — pc1/2/3_br1 will use this as their default gateway" \
    docker exec r2_br1 ip addr add 192.168.100.65/26 dev eth0

echo "  eth1 → net_servico | Subnet: 192.168.100.0/26 | Range: .1–.62"
echo ""
run_cmd "Remove Docker's auto-assigned IP from eth1 to avoid duplicate addresses" \
    docker exec r2_br1 ip addr flush dev eth1

run_cmd "Assign backbone identity of r2_br1 — other routers use this IP as next-hop" \
    docker exec r2_br1 ip addr add 192.168.100.2/26 dev eth1

# ── r3_br2 ────────────────────────────────────────────────────
echo ""
echo "  ┌─ [r3_br2] Branch 2 Router ───────────────────────────┐"
echo "  │  Role: connects Polo 2 clients to the backbone       │"
echo "  │  ip_forward=1 allows it to route between both        │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""
echo "  eth0 → net_polo2 | Subnet: 192.168.100.128/26 | Range: .129–.190"
echo ""
run_cmd "Remove Docker's auto-assigned IP from eth0 to avoid duplicate addresses" \
    docker exec r3_br2 ip addr flush dev eth0

run_cmd "Assign gateway IP for net_polo2 — pc1/2/3_br2 will use this as their default gateway" \
    docker exec r3_br2 ip addr add 192.168.100.129/26 dev eth0

echo "  eth1 → net_servico | Subnet: 192.168.100.0/26 | Range: .1–.62"
echo ""
run_cmd "Remove Docker's auto-assigned IP from eth1 to avoid duplicate addresses" \
    docker exec r3_br2 ip addr flush dev eth1

run_cmd "Assign backbone identity of r3_br2 — other routers use this IP as next-hop" \
    docker exec r3_br2 ip addr add 192.168.100.3/26 dev eth1

# ── r4_edge ───────────────────────────────────────────────────
echo ""
echo "  ┌─ [r4_edge] Edge Router (Internet Gateway) ───────────┐"
echo "  │  Role: border between internal network and internet  │"
echo "  │  Will perform NAT so internal hosts reach internet   │"
echo "  │  ip_forward=1 allows it to route between both        │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""
echo "  eth0 → net_internet | Subnet: 203.0.113.0/24 | Range: .1–.254"
echo ""
run_cmd "Remove Docker's auto-assigned IP from eth0 to avoid duplicate addresses" \
    docker exec r4_edge ip addr flush dev eth0

run_cmd "Assign public-facing IP — this is what internal hosts appear as on the internet after NAT" \
    docker exec r4_edge ip addr add 203.0.113.1/24 dev eth0

echo "  eth1 → net_servico | Subnet: 192.168.100.0/26 | Range: .1–.62"
echo ""
run_cmd "Remove Docker's auto-assigned IP from eth1 to avoid duplicate addresses" \
    docker exec r4_edge ip addr flush dev eth1

run_cmd "Assign backbone identity of r4_edge — internal routers use this as next-hop for internet traffic" \
    docker exec r4_edge ip addr add 192.168.100.4/26 dev eth1

echo "============================================================"
echo "  Router IPs assigned."
echo "  Run: bash scripts/01_routers/test.sh   to verify"
echo "============================================================"
