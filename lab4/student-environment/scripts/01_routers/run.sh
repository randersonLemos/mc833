#!/bin/bash
# =============================================================
# 01_assign_routers.sh — Assign IPs to routers
#
# Routers are the devices that connect two networks.
# Each router has TWO interfaces (eth0 and eth1), so it gets
# TWO IP addresses — one for each network it bridges.
#
# Interface mapping (from docker-compose.yml priority field):
#   r1_hq:   eth0=net_gerencia  | eth1=net_servico
#   r2_br1:  eth0=net_polo1     | eth1=net_servico
#   r3_br2:  eth0=net_polo2     | eth1=net_servico
#   r4_edge: eth0=net_internet  | eth1=net_servico
#
# By convention, we assign .1 of each subnet to the router
# interface on that subnet — this is the GATEWAY address.
#
# IMPORTANT — flush before assign:
# Docker auto-assigns a random IP (172.x.x.x) to every interface
# at container boot. If we just run "ip addr add", our static IP
# is added alongside Docker's IP (two IPs on the same interface).
# To keep a clean state we flush each interface first, then assign.
# =============================================================

echo ""
echo "============================================================"
echo "  STEP 1a — Router IP Assignment"
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
echo "    eth0 → net_gerencia (Management)"
echo "           Subnet : 192.168.100.192/26"
echo "           Range  : 192.168.100.193 – 192.168.100.254"
echo "           Assign : 192.168.100.193  ← acts as gateway for admin_pc"
docker exec r1_hq ip addr flush dev eth0
docker exec r1_hq ip addr add 192.168.100.193/26 dev eth0
echo "           Status : done"
echo ""
echo "    eth1 → net_servico (Backbone)"
echo "           Subnet : 192.168.100.0/26"
echo "           Range  : 192.168.100.1 – 192.168.100.62"
echo "           Assign : 192.168.100.1  ← backbone identity of r1_hq"
docker exec r1_hq ip addr flush dev eth1
docker exec r1_hq ip addr add 192.168.100.1/26 dev eth1
echo "           Status : done"

# ── r2_br1 ────────────────────────────────────────────────────
echo ""
echo "  ┌─ [r2_br1] Branch 1 Router ───────────────────────────┐"
echo "  │  Role: connects Polo 1 clients to the backbone       │"
echo "  │  ip_forward=1 allows it to route between both        │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""
echo "    eth0 → net_polo1 (Branch 1)"
echo "           Subnet : 192.168.100.64/26"
echo "           Range  : 192.168.100.65 – 192.168.100.126"
echo "           Assign : 192.168.100.65  ← acts as gateway for pc1/2/3_br1"
docker exec r2_br1 ip addr flush dev eth0
docker exec r2_br1 ip addr add 192.168.100.65/26 dev eth0
echo "           Status : done"
echo ""
echo "    eth1 → net_servico (Backbone)"
echo "           Subnet : 192.168.100.0/26"
echo "           Range  : 192.168.100.1 – 192.168.100.62"
echo "           Assign : 192.168.100.2  ← backbone identity of r2_br1"
docker exec r2_br1 ip addr flush dev eth1
docker exec r2_br1 ip addr add 192.168.100.2/26 dev eth1
echo "           Status : done"

# ── r3_br2 ────────────────────────────────────────────────────
echo ""
echo "  ┌─ [r3_br2] Branch 2 Router ───────────────────────────┐"
echo "  │  Role: connects Polo 2 clients to the backbone       │"
echo "  │  ip_forward=1 allows it to route between both        │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""
echo "    eth0 → net_polo2 (Branch 2)"
echo "           Subnet : 192.168.100.128/26"
echo "           Range  : 192.168.100.129 – 192.168.100.190"
echo "           Assign : 192.168.100.129  ← acts as gateway for pc1/2/3_br2"
docker exec r3_br2 ip addr flush dev eth0
docker exec r3_br2 ip addr add 192.168.100.129/26 dev eth0
echo "           Status : done"
echo ""
echo "    eth1 → net_servico (Backbone)"
echo "           Subnet : 192.168.100.0/26"
echo "           Range  : 192.168.100.1 – 192.168.100.62"
echo "           Assign : 192.168.100.3  ← backbone identity of r3_br2"
docker exec r3_br2 ip addr flush dev eth1
docker exec r3_br2 ip addr add 192.168.100.3/26 dev eth1
echo "           Status : done"

# ── r4_edge ───────────────────────────────────────────────────
echo ""
echo "  ┌─ [r4_edge] Edge Router (Internet Gateway) ───────────┐"
echo "  │  Role: border between internal network and internet  │"
echo "  │  Will perform NAT so internal hosts reach internet   │"
echo "  │  ip_forward=1 allows it to route between both        │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""
echo "    eth0 → net_internet (Simulated Public Internet)"
echo "           Subnet : 203.0.113.0/24"
echo "           Range  : 203.0.113.1 – 203.0.113.254"
echo "           Assign : 203.0.113.1  ← public-facing IP, used for NAT"
docker exec r4_edge ip addr flush dev eth0
docker exec r4_edge ip addr add 203.0.113.1/24 dev eth0
echo "           Status : done"
echo ""
echo "    eth1 → net_servico (Backbone)"
echo "           Subnet : 192.168.100.0/26"
echo "           Range  : 192.168.100.1 – 192.168.100.62"
echo "           Assign : 192.168.100.4  ← backbone identity of r4_edge"
docker exec r4_edge ip addr flush dev eth1
docker exec r4_edge ip addr add 192.168.100.4/26 dev eth1
echo "           Status : done"

echo ""
echo "============================================================"
echo "  Router IPs assigned."
echo "  Run: bash scripts/01_test_routers.sh to verify"
echo "============================================================"
