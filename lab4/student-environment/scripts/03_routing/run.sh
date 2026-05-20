#!/bin/bash
# =============================================================
# 03_routing/run.sh — Configure static routes
#
# After IP assignment, each device only knows about its own
# subnet (via the kernel connected route). To reach anything
# outside that subnet, every device needs to know where to
# send the packet next. That "next hop" is called the gateway.
#
# Two types of configuration here:
#
#   1. END HOSTS — get a single default route pointing to their
#      local router. "Send everything you don't know about to
#      my gateway."
#
#   2. ROUTERS — get specific routes to subnets they are not
#      directly connected to. Since all routers share net_servico,
#      they can reach each other directly as next hops.
# =============================================================

echo ""
echo "============================================================"
echo "  STEP 3 — Static Routing"
echo "============================================================"
echo "  Devices only know their own subnet after IP assignment."
echo "  This step teaches every device where to forward traffic"
echo "  that is destined outside its local subnet."
echo "============================================================"

# ── ROUTERS ───────────────────────────────────────────────────
# Routers already know two subnets (directly connected).
# They need explicit routes for all other subnets, plus a
# default route to r4_edge for internet-bound traffic.
# All next-hops are reachable directly via net_servico.
# =============================================================

echo ""
echo "  ┌─ Router Routes ──────────────────────────────────────┐"
echo "  │  Routers share net_servico, so they can use each     │"
echo "  │  other as next-hops directly (no extra hops needed). │"
echo "  └──────────────────────────────────────────────────────┘"

# ── r1_hq ─────────────────────────────────────────────────────
# Knows: net_gerencia (.192/26) and net_servico (.0/26)
# Needs: polo1, polo2, and internet
echo ""
echo "  [r1_hq] already knows: net_gerencia, net_servico"
echo "          adding routes to: net_polo1, net_polo2, internet"
echo ""
echo "          net_polo1 (192.168.100.64/26) via r2_br1 (192.168.100.2)"
docker exec r1_hq ip route add 192.168.100.64/26 via 192.168.100.2
echo "          Status : done"
echo ""
echo "          net_polo2 (192.168.100.128/26) via r3_br2 (192.168.100.3)"
docker exec r1_hq ip route add 192.168.100.128/26 via 192.168.100.3
echo "          Status : done"
echo ""
echo "          default (internet) via r4_edge (192.168.100.4)"
docker exec r1_hq ip route add default via 192.168.100.4
echo "          Status : done"

# ── r2_br1 ────────────────────────────────────────────────────
# Knows: net_polo1 (.64/26) and net_servico (.0/26)
# Needs: polo2, gerencia, and internet
echo ""
echo "  [r2_br1] already knows: net_polo1, net_servico"
echo "           adding routes to: net_polo2, net_gerencia, internet"
echo ""
echo "           net_polo2 (192.168.100.128/26) via r3_br2 (192.168.100.3)"
docker exec r2_br1 ip route add 192.168.100.128/26 via 192.168.100.3
echo "           Status : done"
echo ""
echo "           net_gerencia (192.168.100.192/26) via r1_hq (192.168.100.1)"
docker exec r2_br1 ip route add 192.168.100.192/26 via 192.168.100.1
echo "           Status : done"
echo ""
echo "           default (internet) via r4_edge (192.168.100.4)"
docker exec r2_br1 ip route add default via 192.168.100.4
echo "           Status : done"

# ── r3_br2 ────────────────────────────────────────────────────
# Knows: net_polo2 (.128/26) and net_servico (.0/26)
# Needs: polo1, gerencia, and internet
echo ""
echo "  [r3_br2] already knows: net_polo2, net_servico"
echo "           adding routes to: net_polo1, net_gerencia, internet"
echo ""
echo "           net_polo1 (192.168.100.64/26) via r2_br1 (192.168.100.2)"
docker exec r3_br2 ip route add 192.168.100.64/26 via 192.168.100.2
echo "           Status : done"
echo ""
echo "           net_gerencia (192.168.100.192/26) via r1_hq (192.168.100.1)"
docker exec r3_br2 ip route add 192.168.100.192/26 via 192.168.100.1
echo "           Status : done"
echo ""
echo "           default (internet) via r4_edge (192.168.100.4)"
docker exec r3_br2 ip route add default via 192.168.100.4
echo "           Status : done"

# ── r4_edge ───────────────────────────────────────────────────
# Knows: net_internet (203.0.113.0/24) and net_servico (.0/26)
# Needs: polo1, polo2, gerencia — so NAT reply packets can
# find their way back to the correct internal subnet.
# No default needed — r4_edge IS the internet gateway.
echo ""
echo "  [r4_edge] already knows: net_internet, net_servico"
echo "            adding routes to: net_polo1, net_polo2, net_gerencia"
echo "            (needed so NAT reply packets reach internal hosts)"
echo ""
echo "            net_polo1 (192.168.100.64/26) via r2_br1 (192.168.100.2)"
docker exec r4_edge ip route add 192.168.100.64/26 via 192.168.100.2
echo "            Status : done"
echo ""
echo "            net_polo2 (192.168.100.128/26) via r3_br2 (192.168.100.3)"
docker exec r4_edge ip route add 192.168.100.128/26 via 192.168.100.3
echo "            Status : done"
echo ""
echo "            net_gerencia (192.168.100.192/26) via r1_hq (192.168.100.1)"
docker exec r4_edge ip route add 192.168.100.192/26 via 192.168.100.1
echo "            Status : done"

# ── END HOSTS ─────────────────────────────────────────────────
# Each host gets a single default route pointing to its
# local router (gateway). Any traffic outside the local
# subnet is forwarded there.
# =============================================================

echo ""
echo "  ┌─ Host Default Gateways ──────────────────────────────┐"
echo "  │  Each host sends unknown traffic to its local router. │"
echo "  │  The router then handles forwarding from there.       │"
echo "  └──────────────────────────────────────────────────────┘"

# ── Corporate servers (net_servico) ───────────────────────────
# Servers sit on net_servico alongside all routers.
# Their default points to r4_edge for internet access.
echo ""
echo "  [net_servico servers] default via r4_edge (192.168.100.4)"
docker exec srv_dns ip route add default via 192.168.100.4
echo "    srv_dns : done"
docker exec srv_web ip route add default via 192.168.100.4
echo "    srv_web : done"
docker exec srv_db  ip route add default via 192.168.100.4
echo "    srv_db  : done"

# ── Polo 1 clients (net_polo1) ────────────────────────────────
echo ""
echo "  [net_polo1 clients] default via r2_br1 (192.168.100.65)"
docker exec pc1_br1 ip route add default via 192.168.100.65
echo "    pc1_br1 : done"
docker exec pc2_br1 ip route add default via 192.168.100.65
echo "    pc2_br1 : done"
docker exec pc3_br1 ip route add default via 192.168.100.65
echo "    pc3_br1 : done"

# ── Polo 2 clients (net_polo2) ────────────────────────────────
echo ""
echo "  [net_polo2 clients] default via r3_br2 (192.168.100.129)"
docker exec pc1_br2 ip route add default via 192.168.100.129
echo "    pc1_br2 : done"
docker exec pc2_br2 ip route add default via 192.168.100.129
echo "    pc2_br2 : done"
docker exec pc3_br2 ip route add default via 192.168.100.129
echo "    pc3_br2 : done"

# ── Management (net_gerencia) ──────────────────────────────────
echo ""
echo "  [net_gerencia] default via r1_hq (192.168.100.193)"
docker exec admin_pc ip route add default via 192.168.100.193
echo "    admin_pc : done"

# ── Internet devices (net_internet) ───────────────────────────
echo ""
echo "  [net_internet] default via r4_edge (203.0.113.1)"
docker exec srv_public_web ip route add default via 203.0.113.1
echo "    srv_public_web : done"
docker exec ext_client ip route add default via 203.0.113.1
echo "    ext_client     : done"

echo ""
echo "============================================================"
echo "  Routing configured."
echo "  Run: bash scripts/03_routing/test.sh   to verify"
echo "============================================================"
