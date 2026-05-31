#!/bin/bash
# =============================================================
# 01_routers/run.sh — Assign IPs to routers
#
# Docker does not guarantee which interface (eth0 or eth1) is
# connected to which network — the assignment varies between runs
# and the priority field in docker-compose.yml is not reliable.
#
# Strategy: Docker always assigns a temporary 172.x.x.x IP to each
# container interface when it starts. We use that IP to identify
# which interface belongs to which network, then assign our static
# IPs to the correct interfaces.
#
# Logical assignments (IPs never change; only the interface name may):
#   r1_hq  : net_gerencia=192.168.100.193/26  net_servico=192.168.100.1/26
#   r2_br1 : net_polo1=192.168.100.65/26      net_servico=192.168.100.2/26
#   r3_br2 : net_polo2=192.168.100.129/26     net_servico=192.168.100.3/26
#   r4_edge: net_internet=203.0.113.1/24      net_servico=192.168.100.4/26
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

# find_iface CONTAINER NETWORK
#
# Returns the interface name (eth0 or eth1) that is connected to NETWORK.
#
# How it works:
#   1. Ask Docker which 172.x.x.x IP it assigned to CONTAINER on NETWORK
#   2. Look for that IP inside the container to identify the interface
find_iface() {
    local container="$1"
    local network="student-environment_$2"

    local docker_ip
    docker_ip=$(docker network inspect "$network" \
        | grep -A4 "\"Name\": \"${container}\"" \
        | grep "IPv4Address" \
        | grep -oE '172\.[0-9]+\.[0-9]+\.[0-9]+')

    docker exec "$container" ip addr show \
        | awk -v ip="$docker_ip" '
            /^[0-9]+:/ { split($2, a, "@"); iface = a[1]; gsub(/:$/, "", iface) }
            /inet /    { if ($2 ~ ip) print iface }
          '
}

echo ""
echo "============================================================"
echo "  STEP 1 — Router IP Assignment"
echo "============================================================"
echo "  Routers are the only devices with two interfaces."
echo "  Each interface connects to a different subnet."
echo "  Interfaces are detected at runtime because Docker does"
echo "  not guarantee which interface maps to which network."
echo "============================================================"

# ── r1_hq ─────────────────────────────────────────────────────
echo ""
echo "  ┌─ [r1_hq] Headquarters Router ────────────────────────┐"
echo "  │  Role: connects Management to the backbone           │"
echo "  │  ip_forward=1 allows it to route between both        │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""

R1_GERENCIA=$(find_iface r1_hq net_gerencia)
R1_SERVICO=$(find_iface r1_hq net_servico)
printf "    Detected: net_gerencia=%s  net_servico=%s\n\n" "$R1_GERENCIA" "$R1_SERVICO"

echo "  $R1_GERENCIA → net_gerencia | 192.168.100.192/26 | Range: .193–.254"
echo ""
run_cmd "Remove Docker's auto-assigned IP from $R1_GERENCIA" \
    docker exec r1_hq ip addr flush dev "$R1_GERENCIA"
run_cmd "Assign gateway IP for net_gerencia — admin_pc will use this as default gateway" \
    docker exec r1_hq ip addr add 192.168.100.193/26 dev "$R1_GERENCIA"

echo "  $R1_SERVICO → net_servico | 192.168.100.0/26 | Range: .1–.62"
echo ""
run_cmd "Remove Docker's auto-assigned IP from $R1_SERVICO" \
    docker exec r1_hq ip addr flush dev "$R1_SERVICO"
run_cmd "Assign backbone identity of r1_hq — other routers use this IP as next-hop" \
    docker exec r1_hq ip addr add 192.168.100.1/26 dev "$R1_SERVICO"

# ── r2_br1 ────────────────────────────────────────────────────
echo ""
echo "  ┌─ [r2_br1] Branch 1 Router ───────────────────────────┐"
echo "  │  Role: connects Polo 1 clients to the backbone       │"
echo "  │  ip_forward=1 allows it to route between both        │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""

R2_POLO1=$(find_iface r2_br1 net_polo1)
R2_SERVICO=$(find_iface r2_br1 net_servico)
printf "    Detected: net_polo1=%s  net_servico=%s\n\n" "$R2_POLO1" "$R2_SERVICO"

echo "  $R2_POLO1 → net_polo1 | 192.168.100.64/26 | Range: .65–.126"
echo ""
run_cmd "Remove Docker's auto-assigned IP from $R2_POLO1" \
    docker exec r2_br1 ip addr flush dev "$R2_POLO1"
run_cmd "Assign gateway IP for net_polo1 — pc1/2/3_br1 will use this as default gateway" \
    docker exec r2_br1 ip addr add 192.168.100.65/26 dev "$R2_POLO1"

echo "  $R2_SERVICO → net_servico | 192.168.100.0/26 | Range: .1–.62"
echo ""
run_cmd "Remove Docker's auto-assigned IP from $R2_SERVICO" \
    docker exec r2_br1 ip addr flush dev "$R2_SERVICO"
run_cmd "Assign backbone identity of r2_br1 — other routers use this IP as next-hop" \
    docker exec r2_br1 ip addr add 192.168.100.2/26 dev "$R2_SERVICO"

# ── r3_br2 ────────────────────────────────────────────────────
echo ""
echo "  ┌─ [r3_br2] Branch 2 Router ───────────────────────────┐"
echo "  │  Role: connects Polo 2 clients to the backbone       │"
echo "  │  ip_forward=1 allows it to route between both        │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""

R3_POLO2=$(find_iface r3_br2 net_polo2)
R3_SERVICO=$(find_iface r3_br2 net_servico)
printf "    Detected: net_polo2=%s  net_servico=%s\n\n" "$R3_POLO2" "$R3_SERVICO"

echo "  $R3_POLO2 → net_polo2 | 192.168.100.128/26 | Range: .129–.190"
echo ""
run_cmd "Remove Docker's auto-assigned IP from $R3_POLO2" \
    docker exec r3_br2 ip addr flush dev "$R3_POLO2"
run_cmd "Assign gateway IP for net_polo2 — pc1/2/3_br2 will use this as default gateway" \
    docker exec r3_br2 ip addr add 192.168.100.129/26 dev "$R3_POLO2"

echo "  $R3_SERVICO → net_servico | 192.168.100.0/26 | Range: .1–.62"
echo ""
run_cmd "Remove Docker's auto-assigned IP from $R3_SERVICO" \
    docker exec r3_br2 ip addr flush dev "$R3_SERVICO"
run_cmd "Assign backbone identity of r3_br2 — other routers use this IP as next-hop" \
    docker exec r3_br2 ip addr add 192.168.100.3/26 dev "$R3_SERVICO"

# ── r4_edge ───────────────────────────────────────────────────
echo ""
echo "  ┌─ [r4_edge] Edge Router (Internet Gateway) ───────────┐"
echo "  │  Role: border between internal network and internet  │"
echo "  │  Will perform NAT so internal hosts reach internet   │"
echo "  │  ip_forward=1 allows it to route between both        │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""

R4_INTERNET=$(find_iface r4_edge net_internet)
R4_SERVICO=$(find_iface r4_edge net_servico)
printf "    Detected: net_internet=%s  net_servico=%s\n\n" "$R4_INTERNET" "$R4_SERVICO"

echo "  $R4_INTERNET → net_internet | 203.0.113.0/24 | Range: .1–.254"
echo ""
run_cmd "Remove Docker's auto-assigned IP from $R4_INTERNET" \
    docker exec r4_edge ip addr flush dev "$R4_INTERNET"
run_cmd "Assign public-facing IP — internal hosts appear as this after NAT" \
    docker exec r4_edge ip addr add 203.0.113.1/24 dev "$R4_INTERNET"

echo "  $R4_SERVICO → net_servico | 192.168.100.0/26 | Range: .1–.62"
echo ""
run_cmd "Remove Docker's auto-assigned IP from $R4_SERVICO" \
    docker exec r4_edge ip addr flush dev "$R4_SERVICO"
run_cmd "Assign backbone identity of r4_edge — internal routers use this as next-hop for internet" \
    docker exec r4_edge ip addr add 192.168.100.4/26 dev "$R4_SERVICO"

echo "============================================================"
echo "  Router IPs assigned."
echo "  Run: bash scripts/01_routers/test.sh   to verify"
echo "============================================================"
