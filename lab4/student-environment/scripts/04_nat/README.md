# Task 04 — NAT (Network Address Translation)

## What this task does

Enables MASQUERADE NAT on `r4_edge` so all internal hosts can reach
the public internet using a single public-facing IP (`203.0.113.1`).

## The problem this solves

Internal hosts use private IPs (`192.168.100.x`) that only exist inside
the corporate network. The internet has no route back to those addresses.

Without NAT, this is what happens when `pc1_br1` tries to reach the internet:

```
pc1_br1 sends:  src=192.168.100.66  dst=203.0.113.10
srv_public_web receives the packet and tries to reply to 192.168.100.66
Reply is lost — the internet has no route to 192.168.100.x
```

## How MASQUERADE fixes it

`r4_edge` intercepts every outbound packet just before it leaves `eth0`
and rewrites the source IP to its own public IP (`203.0.113.1`).
When the reply arrives, `r4_edge` remembers the original sender and
restores the destination back to the internal IP.

```
Outbound:
  pc1_br1 (192.168.100.66) → r2_br1 → r4_edge
  r4_edge rewrites: src 192.168.100.66 → 203.0.113.1
  → srv_public_web (203.0.113.10)

Inbound reply:
  srv_public_web → r4_edge (203.0.113.1)
  r4_edge restores: dst 203.0.113.1 → 192.168.100.66
  → r2_br1 → pc1_br1
```

The internal host never notices — the translation is transparent.

## The command

```bash
iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
```

| Part | Meaning |
|---|---|
| `-t nat` | operate on the NAT table |
| `-A POSTROUTING` | apply just before the packet leaves the machine |
| `-o eth0` | only for packets exiting through `eth0` (internet side) |
| `-j MASQUERADE` | rewrite source IP to match the outgoing interface IP |

`MASQUERADE` is a dynamic form of SNAT (Source NAT). It automatically
uses whatever IP is currently assigned to `eth0`, which makes it ideal
for this lab since we don't need to hardcode the public IP.

## Why only r4_edge needs this

NAT sits at the boundary between the private network and the internet.
`r4_edge` is the only router with one foot in each world:

- `eth1` → `net_servico` (private, `192.168.100.0/26`)
- `eth0` → `net_internet` (public, `203.0.113.0/24`)

All internal routers (`r1_hq`, `r2_br1`, `r3_br2`) only connect private
subnets to each other — they never touch the internet side, so they
need no NAT configuration.

## How to run

```bash
bash scripts/04_nat/run.sh
bash scripts/04_nat/test.sh
```

## What the test checks

1. **NAT rule presence** — dumps `iptables -t nat -L POSTROUTING` on
   `r4_edge` and confirms the MASQUERADE rule exists
2. **Internet reachability** — pings from every internal subnet
   (`net_polo1`, `net_polo2`, `net_gerencia`) to `srv_public_web`
   (`203.0.113.10`). A timeout means NAT is not translating correctly
3. **Traceroute** — shows the full hop path from `pc1_br1` to
   `srv_public_web`, confirming the packet crosses `r4_edge` before
   reaching the internet
