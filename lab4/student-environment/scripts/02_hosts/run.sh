#!/bin/bash
# =============================================================
# 02_hosts/run.sh — Assign IPs to all end-host devices
#
# End hosts have only ONE interface (eth0), so they get
# a single IP within their subnet.
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
echo "  └──────────────────────────────────────────────────────┘"
echo ""

run_cmd "Remove Docker's auto-assigned IP from srv_dns" \
    docker exec srv_dns ip addr flush dev eth0
run_cmd "Assign static IP to srv_dns — Polo 1 is allowed to reach this server on port 53" \
    docker exec srv_dns ip addr add 192.168.100.10/26 dev eth0

run_cmd "Remove Docker's auto-assigned IP from srv_web" \
    docker exec srv_web ip addr flush dev eth0
run_cmd "Assign static IP to srv_web — Polo 2 is allowed to reach this server on port 80" \
    docker exec srv_web ip addr add 192.168.100.11/26 dev eth0

run_cmd "Remove Docker's auto-assigned IP from srv_db" \
    docker exec srv_db ip addr flush dev eth0
run_cmd "Assign static IP to srv_db — access will be restricted by firewall rules in step 5" \
    docker exec srv_db ip addr add 192.168.100.12/26 dev eth0

# ── net_polo1 — Branch 1 clients ──────────────────────────────
echo ""
echo "  ┌─ [net_polo1] Branch 1 Client PCs ────────────────────┐"
echo "  │  Subnet  : 192.168.100.64/26                         │"
echo "  │  Range   : 192.168.100.65 – 192.168.100.126          │"
echo "  │  Gateway : 192.168.100.65 (r2_br1 eth0)              │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""

run_cmd "Remove Docker's auto-assigned IP from pc1_br1" \
    docker exec pc1_br1 ip addr flush dev eth0
run_cmd "Assign static IP to pc1_br1 within net_polo1 subnet" \
    docker exec pc1_br1 ip addr add 192.168.100.66/26 dev eth0

run_cmd "Remove Docker's auto-assigned IP from pc2_br1" \
    docker exec pc2_br1 ip addr flush dev eth0
run_cmd "Assign static IP to pc2_br1 within net_polo1 subnet" \
    docker exec pc2_br1 ip addr add 192.168.100.67/26 dev eth0

run_cmd "Remove Docker's auto-assigned IP from pc3_br1" \
    docker exec pc3_br1 ip addr flush dev eth0
run_cmd "Assign static IP to pc3_br1 within net_polo1 subnet" \
    docker exec pc3_br1 ip addr add 192.168.100.68/26 dev eth0

# ── net_polo2 — Branch 2 clients ──────────────────────────────
echo ""
echo "  ┌─ [net_polo2] Branch 2 Client PCs ────────────────────┐"
echo "  │  Subnet  : 192.168.100.128/26                        │"
echo "  │  Range   : 192.168.100.129 – 192.168.100.190         │"
echo "  │  Gateway : 192.168.100.129 (r3_br2 eth0)             │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""

run_cmd "Remove Docker's auto-assigned IP from pc1_br2" \
    docker exec pc1_br2 ip addr flush dev eth0
run_cmd "Assign static IP to pc1_br2 within net_polo2 subnet" \
    docker exec pc1_br2 ip addr add 192.168.100.130/26 dev eth0

run_cmd "Remove Docker's auto-assigned IP from pc2_br2" \
    docker exec pc2_br2 ip addr flush dev eth0
run_cmd "Assign static IP to pc2_br2 within net_polo2 subnet" \
    docker exec pc2_br2 ip addr add 192.168.100.131/26 dev eth0

run_cmd "Remove Docker's auto-assigned IP from pc3_br2" \
    docker exec pc3_br2 ip addr flush dev eth0
run_cmd "Assign static IP to pc3_br2 within net_polo2 subnet" \
    docker exec pc3_br2 ip addr add 192.168.100.132/26 dev eth0

# ── net_gerencia — Management ──────────────────────────────────
echo ""
echo "  ┌─ [net_gerencia] Management Network ──────────────────┐"
echo "  │  Subnet  : 192.168.100.192/26                        │"
echo "  │  Range   : 192.168.100.193 – 192.168.100.254         │"
echo "  │  Gateway : 192.168.100.193 (r1_hq eth0)              │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""

run_cmd "Remove Docker's auto-assigned IP from admin_pc" \
    docker exec admin_pc ip addr flush dev eth0
run_cmd "Assign static IP to admin_pc — firewall will isolate this from all Polo subnets" \
    docker exec admin_pc ip addr add 192.168.100.194/26 dev eth0

# ── net_internet — Public internet devices ────────────────────
echo ""
echo "  ┌─ [net_internet] Simulated Public Internet ───────────┐"
echo "  │  Subnet  : 203.0.113.0/24                            │"
echo "  │  Gateway : 203.0.113.1 (r4_edge eth0)                │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""

run_cmd "Remove Docker's auto-assigned IP from srv_public_web" \
    docker exec srv_public_web ip addr flush dev eth0
run_cmd "Assign public IP to srv_public_web — internal hosts will reach it via NAT through r4_edge" \
    docker exec srv_public_web ip addr add 203.0.113.10/24 dev eth0

run_cmd "Remove Docker's auto-assigned IP from ext_client" \
    docker exec ext_client ip addr flush dev eth0
run_cmd "Assign public IP to ext_client — simulates an external attacker blocked by stateful firewall" \
    docker exec ext_client ip addr add 203.0.113.20/24 dev eth0

echo "============================================================"
echo "  Host IPs assigned."
echo "  Run: bash scripts/02_hosts/test.sh   to verify"
echo "============================================================"
