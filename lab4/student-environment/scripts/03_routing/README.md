# Task 03 — Static Routing

## What this task does

Adds static routes so traffic can flow across subnet boundaries.
After IP assignment, every device only knows its own subnet. This task
teaches each device where to forward packets that are destined elsewhere.

## The problem this solves

After Task 02, `pc1_br1` has this routing table:

```
192.168.100.64/26 dev eth0 proto kernel scope link src 192.168.100.66
```

It can reach `pc2_br1` (`.67`) directly — same subnet, same wire.
But if it tries to ping `srv_dns` at `192.168.100.10`, the kernel has
no route for that address and silently drops the packet.

After this task, the routing table becomes:

```
default via 192.168.100.65 dev eth0
192.168.100.64/26 dev eth0 proto kernel scope link src 192.168.100.66
```

Now any unknown destination is forwarded to the gateway (`r2_br1`),
which knows how to reach the rest of the network.

## Two types of configuration

### 1. End hosts — default gateway

End hosts have a single rule: send everything unknown to the local router.

```bash
ip route add default via <gateway>
```

| Device              | Gateway              | Router  |
|---------------------|----------------------|---------|
| pc1/2/3_br1         | 192.168.100.65       | r2_br1  |
| pc1/2/3_br2         | 192.168.100.129      | r3_br2  |
| admin_pc            | 192.168.100.193      | r1_hq   |
| srv_dns/web/db      | 192.168.100.4        | r4_edge |
| srv_public_web      | 203.0.113.1          | r4_edge |
| ext_client          | 203.0.113.1          | r4_edge |

**Why do the servers use r4_edge and not r1_hq as their gateway?**

`srv_dns`, `srv_web` and `srv_db` live on `net_servico` (192.168.100.0/26),
which is the backbone itself. All four routers are on the same `/26`, so the
servers can already reach any of them directly — no gateway needed for that.

The default gateway is only used for traffic going **outside** the `/26`,
which in practice means the internet (`203.0.113.0/24`). Since `r4_edge` is
the internet gateway and is directly reachable on the same subnet, pointing the
servers at it avoids an unnecessary extra hop:

```
# gateway = r1_hq:   srv_dns → r1_hq → r4_edge → internet   (2 hops)
# gateway = r4_edge: srv_dns → r4_edge → internet            (1 hop)
```

`r1_hq` would work but would add a redundant hop for every internet-bound packet.

### 2. Routers — specific routes to remote subnets

After IP assignment, each router only knows the subnets it is directly
connected to. For example, `r2_br1` knows `net_servico` and `net_polo1`,
but has no route for `net_polo2` or `net_gerencia`. If a packet arrives
from a Polo 1 client destined for `admin_pc`, `r2_br1` finds no matching
route and silently drops it. Static routes fix this.

**Why are the next-hops always backbone IPs?**

All four routers share `net_servico` (192.168.100.0/26), so every router
can reach every other router directly — no intermediary needed. This is
why next-hops are always backbone IPs: `r2_br1` does not need to know
the full path to `net_gerencia`, only that the next hop is `r1_hq`
(192.168.100.1), which is directly reachable on the same `/26`.

**Why does r4_edge have no default route?**

The other routers send unknown traffic to `r4_edge` because it is the
internet gateway. `r4_edge` itself already has the internet on its own
interface (`203.0.113.0/24`) — there is no upstream router that knows
more than it does. A default route on `r4_edge` would have nowhere
meaningful to point.

**Why does r4_edge need routes back to internal subnets?**

`r4_edge` performs NAT: when an internal host reaches the internet, the
source IP is rewritten to `203.0.113.1`. When the reply arrives, `r4_edge`
must reverse the translation and deliver the packet back to the original
host. To do that, it needs to know how to reach the internal subnets:

```
192.168.100.64/26  via 192.168.100.2  ← Polo 1 packets go via r2_br1
192.168.100.128/26 via 192.168.100.3  ← Polo 2 packets go via r3_br2
192.168.100.192/26 via 192.168.100.1  ← Management packets go via r1_hq
```

Without these routes, NAT replies would arrive at `r4_edge` with a private
destination IP and be dropped because `r4_edge` would not know where to
forward them.

Routers already know their two directly connected subnets. They need
explicit routes for every other subnet, plus a default route for internet.
All next-hops are reachable directly via `net_servico`.

**Why does r1_hq not appear in the static routes table with a route to net_gerencia?**

The static routes table only shows what was **manually configured**. `r1_hq`
does not need a static route to `net_gerencia` because it is directly connected
to it — that route already exists as a connected route created automatically by
the kernel in step 1:

```
192.168.100.192/26 dev eth0 proto kernel  ← created automatically
```

All routers can reach net_gerencia — the path each one takes:

| Router  | How it reaches net_gerencia |
|---|---|
| r1_hq   | Directly connected — delivers on its own interface |
| r2_br1  | Static route → via 192.168.100.1 (r1_hq) |
| r3_br2  | Static route → via 192.168.100.1 (r1_hq) |
| r4_edge | Static route → via 192.168.100.1 (r1_hq) |

```bash
ip route add <subnet> via <next-hop>
ip route add default via <internet-gateway>
```

#### r1_hq
Knows: `net_gerencia`, `net_servico`

| Destination          | Via                         |
|----------------------|-----------------------------|
| 192.168.100.64/26    | 192.168.100.2 (r2_br1 eth1) |
| 192.168.100.128/26   | 192.168.100.3 (r3_br2 eth1) |
| default              | 192.168.100.4 (r4_edge eth1)|

#### r2_br1
Knows: `net_polo1`, `net_servico`

| Destination          | Via                         |
|----------------------|-----------------------------|
| 192.168.100.128/26   | 192.168.100.3 (r3_br2 eth1) |
| 192.168.100.192/26   | 192.168.100.1 (r1_hq eth1)  |
| default              | 192.168.100.4 (r4_edge eth1)|

#### r3_br2
Knows: `net_polo2`, `net_servico`

| Destination          | Via                         |
|----------------------|-----------------------------|
| 192.168.100.64/26    | 192.168.100.2 (r2_br1 eth1) |
| 192.168.100.192/26   | 192.168.100.1 (r1_hq eth1)  |
| default              | 192.168.100.4 (r4_edge eth1)|

#### r4_edge
Knows: `net_internet`, `net_servico`

No default route needed — r4_edge **is** the internet gateway.
It needs routes back to internal subnets so NAT reply packets
can find their way to the correct host after de-masquerading.

| Destination          | Via                         |
|----------------------|-----------------------------|
| 192.168.100.64/26    | 192.168.100.2 (r2_br1 eth1) |
| 192.168.100.128/26   | 192.168.100.3 (r3_br2 eth1) |
| 192.168.100.192/26   | 192.168.100.1 (r1_hq eth1)  |

## How to run

```bash
bash scripts/03_routing/run.sh
bash scripts/03_routing/test.sh
```

## What the test checks

1. **Routing tables** — prints `ip route` for every device to confirm
   the default gateway and static routes are present
2. **Cross-subnet ping** — verifies packets actually travel across subnet
   boundaries through the routers. Note: Polo 1 ↔ Polo 2 and Polo → Management
   pings will **pass here** since the firewall is not applied yet — they will
   be blocked in Task 05
3. **Traceroute** — shows the exact hop-by-hop path from `pc1_br1` to
   `srv_dns`, confirming traffic flows through `r2_br1` before reaching
   the server
