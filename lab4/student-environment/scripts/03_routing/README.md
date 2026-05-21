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

### 2. Routers — specific routes to remote subnets

Routers already know their two directly connected subnets. They need
explicit routes for every other subnet, plus a default route for internet.
All next-hops are reachable directly via `net_servico`.

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
