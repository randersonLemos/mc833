#!/bin/bash
# =============================================================
# 02_hosts/run.sh — Assign IPs to all end-host devices
#
# End hosts have only ONE interface (eth0), so they get
# a single IP within their subnet.
# Each interface is flushed first to remove Docker's auto-assigned
# IP before we add our static one.
# =============================================================

echo ""
echo "============================================================"
echo "  STEP 2 — Host IP Assignment"
echo "============================================================"
echo "  End hosts have a single interface (eth0)."
echo "  Unlike routers, they do not forward traffic."
echo "  Each host gets one IP within its subnet."
echo "============================================================"

# ── net_servico — Corporate servers ───────────────────────────
echo ""
echo "  ┌─ [net_servico] Corporate Servers ────────────────────┐"
echo "  │  Subnet  : 192.168.100.0/26                          │"
echo "  │  Range   : 192.168.100.1 – 192.168.100.62            │"
echo "  │  Gateway : 192.168.100.1 (r1_hq eth1)                │"
echo "  │  These servers are reachable by internal networks    │"
echo "  │  according to the security policy defined later.     │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""
echo "    eth0 → net_servico"
echo "           Subnet : 192.168.100.0/26"
echo "           Assign : 192.168.100.10  ← srv_dns (DNS server)"
docker exec srv_dns ip addr flush dev eth0 && docker exec srv_dns ip addr add 192.168.100.10/26 dev eth0
echo "           Status : done"
echo ""
echo "           Assign : 192.168.100.11  ← srv_web (Web server — HTTP)"
docker exec srv_web ip addr flush dev eth0 && docker exec srv_web ip addr add 192.168.100.11/26 dev eth0
echo "           Status : done"
echo ""
echo "           Assign : 192.168.100.12  ← srv_db (Database — access restricted by firewall)"
docker exec srv_db ip addr flush dev eth0 && docker exec srv_db ip addr add 192.168.100.12/26 dev eth0
echo "           Status : done"

# ── net_polo1 — Branch 1 clients ──────────────────────────────
echo ""
echo "  ┌─ [net_polo1] Branch 1 Client PCs ────────────────────┐"
echo "  │  Subnet  : 192.168.100.64/26                         │"
echo "  │  Range   : 192.168.100.65 – 192.168.100.126          │"
echo "  │  Gateway : 192.168.100.65 (r2_br1 eth0)              │"
echo "  │  Traffic from these PCs exits via r2_br1 into the    │"
echo "  │  backbone. Internet access goes through r4_edge NAT. │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""
echo "    eth0 → net_polo1"
echo "           Subnet : 192.168.100.64/26"
echo "           Assign : 192.168.100.66  ← pc1_br1"
docker exec pc1_br1 ip addr flush dev eth0 && docker exec pc1_br1 ip addr add 192.168.100.66/26 dev eth0
echo "           Status : done"
echo ""
echo "           Assign : 192.168.100.67  ← pc2_br1"
docker exec pc2_br1 ip addr flush dev eth0 && docker exec pc2_br1 ip addr add 192.168.100.67/26 dev eth0
echo "           Status : done"
echo ""
echo "           Assign : 192.168.100.68  ← pc3_br1"
docker exec pc3_br1 ip addr flush dev eth0 && docker exec pc3_br1 ip addr add 192.168.100.68/26 dev eth0
echo "           Status : done"

# ── net_polo2 — Branch 2 clients ──────────────────────────────
echo ""
echo "  ┌─ [net_polo2] Branch 2 Client PCs ────────────────────┐"
echo "  │  Subnet  : 192.168.100.128/26                        │"
echo "  │  Range   : 192.168.100.129 – 192.168.100.190         │"
echo "  │  Gateway : 192.168.100.129 (r3_br2 eth0)             │"
echo "  │  Isolated from Polo 1 — firewall will block          │"
echo "  │  any cross-branch traffic bidirectionally.           │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""
echo "    eth0 → net_polo2"
echo "           Subnet : 192.168.100.128/26"
echo "           Assign : 192.168.100.130  ← pc1_br2"
docker exec pc1_br2 ip addr flush dev eth0 && docker exec pc1_br2 ip addr add 192.168.100.130/26 dev eth0
echo "           Status : done"
echo ""
echo "           Assign : 192.168.100.131  ← pc2_br2"
docker exec pc2_br2 ip addr flush dev eth0 && docker exec pc2_br2 ip addr add 192.168.100.131/26 dev eth0
echo "           Status : done"
echo ""
echo "           Assign : 192.168.100.132  ← pc3_br2"
docker exec pc3_br2 ip addr flush dev eth0 && docker exec pc3_br2 ip addr add 192.168.100.132/26 dev eth0
echo "           Status : done"

# ── net_gerencia — Management ──────────────────────────────────
echo ""
echo "  ┌─ [net_gerencia] Management Network ──────────────────┐"
echo "  │  Subnet  : 192.168.100.192/26                        │"
echo "  │  Range   : 192.168.100.193 – 192.168.100.254         │"
echo "  │  Gateway : 192.168.100.193 (r1_hq eth0)              │"
echo "  │  Highly restricted — Polos cannot reach this subnet. │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""
echo "    eth0 → net_gerencia"
echo "           Subnet : 192.168.100.192/26"
echo "           Assign : 192.168.100.194  ← admin_pc"
docker exec admin_pc ip addr flush dev eth0 && docker exec admin_pc ip addr add 192.168.100.194/26 dev eth0
echo "           Status : done"

# ── net_internet — Simulated internet ─────────────────────────
echo ""
echo "  ┌─ [net_internet] Simulated Public Internet ───────────┐"
echo "  │  Subnet  : 203.0.113.0/24                            │"
echo "  │  Gateway : 203.0.113.1 (r4_edge eth0)                │"
echo "  │  These devices simulate the public internet.         │"
echo "  │  Internal hosts reach them via NAT on r4_edge.       │"
echo "  │  ext_client simulates an outside attacker — it will  │"
echo "  │  be blocked from initiating connections inward.      │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""
echo "    eth0 → net_internet"
echo "           Subnet : 203.0.113.0/24"
echo "           Assign : 203.0.113.10  ← srv_public_web (target for NAT test)"
docker exec srv_public_web ip addr flush dev eth0 && docker exec srv_public_web ip addr add 203.0.113.10/24 dev eth0
echo "           Status : done"
echo ""
echo "           Assign : 203.0.113.20  ← ext_client (simulated external attacker)"
docker exec ext_client ip addr flush dev eth0 && docker exec ext_client ip addr add 203.0.113.20/24 dev eth0
echo "           Status : done"

echo ""
echo "============================================================"
echo "  Host IPs assigned."
echo "  Run: bash scripts/02_hosts/test.sh   to verify"
echo "============================================================"
