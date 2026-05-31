#!/bin/bash
# =============================================================
# 04_nat/run.sh — Configure NAT on r4_edge
#
# Internal hosts use private IPs (192.168.100.x) that the
# internet cannot route back to. MASQUERADE NAT on r4_edge
# rewrites the source IP to its public-facing IP (203.0.113.1)
# so replies can find their way back.
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
echo "  STEP 4 — NAT Configuration"
echo "============================================================"
echo "  Internal hosts use private IPs (192.168.100.x) that"
echo "  the internet cannot route back to. NAT on r4_edge"
echo "  translates those IPs to its own public IP (203.0.113.1)"
echo "  so replies can find their way back."
echo "============================================================"

echo ""
echo "  ┌─ [r4_edge] MASQUERADE NAT ───────────────────────────┐"
echo "  │  Applied on eth0 (internet-facing interface).         │"
echo "  │                                                        │"
echo "  │  Outbound: src 192.168.100.66 → rewritten to .113.1   │"
echo "  │  Inbound:  dst 203.0.113.1   → restored to .100.66   │"
echo "  │                                                        │"
echo "  │  -t nat         : operate on the NAT table            │"
echo "  │  -A POSTROUTING : apply just before packet leaves     │"
echo "  │  -o eth0        : only on packets leaving via eth0    │"
echo "  │  -j MASQUERADE  : rewrite src IP to interface IP      │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""

R4_INTERNET=$(docker exec r4_edge ip addr show \
    | awk '/^[0-9]+:/ { split($2,a,"@"); iface=a[1]; gsub(/:$/,"",iface) }
           /inet / && $2 ~ /203\.0\.113/ { print iface }')
printf "    Detected: net_internet interface on r4_edge = %s\n\n" "$R4_INTERNET"

run_cmd "Enable MASQUERADE on $R4_INTERNET so all internal hosts can reach the internet using r4_edge's public IP" \
    docker exec r4_edge iptables -t nat -A POSTROUTING -o "$R4_INTERNET" -j MASQUERADE

echo "============================================================"
echo "  NAT configured."
echo "  Run: bash scripts/04_nat/test.sh   to verify"
echo "============================================================"
