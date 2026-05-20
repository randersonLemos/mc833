# Task 01 — Router IP Assignment

## What this task does

Assigns static IP addresses to all four routers in the network.

## Why routers are configured first

Routers bridge two subnets each. Their IPs define the **gateway address**
for every device on those subnets. Everything else depends on these addresses
being correct before static routes and firewall rules are applied.

## How it works

Each router has two interfaces, assigned based on the `priority` field in
`docker-compose.yml`:

| Router   | eth0 (local subnet)  | eth1 (backbone net_servico) |
|----------|----------------------|-----------------------------|
| r1_hq    | 192.168.100.193/26   | 192.168.100.1/26            |
| r2_br1   | 192.168.100.65/26    | 192.168.100.2/26            |
| r3_br2   | 192.168.100.129/26   | 192.168.100.3/26            |
| r4_edge  | 203.0.113.1/24       | 192.168.100.4/26            |

### The flush + assign pattern

Docker automatically assigns a random IP (`172.x.x.x`) to every interface
at container boot. To avoid having two IPs on the same interface, each
interface is flushed before the static IP is added:

```bash
docker exec r2_br1 ip addr flush dev eth0
docker exec r2_br1 ip addr add 192.168.100.65/26 dev eth0
```

## How to run

```bash
bash scripts/01_routers/run.sh
bash scripts/01_routers/test.sh
```

## What the test checks

1. **Interface check** — each IP is on the correct interface (eth0 or eth1)
2. **Ping reachability** — all routers can reach each other on `net_servico`
   without any static routes (same subnet = direct delivery)
3. **Kernel routing table** — prints `ip route` for each router to confirm
   the kernel created connected routes automatically
