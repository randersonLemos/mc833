# Task 02 — Host IP Assignment

## What this task does

Assigns static IP addresses to all end-host devices: servers, branch
client PCs, the admin workstation, and the simulated internet devices.

## Why hosts are configured after routers

Hosts have a single interface and a single IP. They don't route traffic —
they just send it to their gateway (the router). The routers must exist
and have IPs before we can define which gateway each host will use in the
next step (routing).

## What happens when an IP is assigned

When `ip addr add 192.168.100.66/26 dev eth0` runs on `pc1_br1`, the
kernel automatically creates a **connected route** for the entire subnet:

```
192.168.100.64/26 dev eth0 proto kernel scope link src 192.168.100.66
```

This means `pc1_br1` can already reach other hosts in the same subnet
(`.67`, `.68`) directly — no router needed, same wire.

However, there is **no default route** yet. Any traffic destined outside
`192.168.100.64/26` (other subnets, internet) will fail because the host
doesn't know where to send it. That is fixed in the next task (routing),
which adds:

```
ip route add default via 192.168.100.65
```

After that, the routing table becomes:

```
default via 192.168.100.65 dev eth0
192.168.100.64/26 dev eth0 proto kernel scope link src 192.168.100.66
```

## IP assignments

### Corporate servers — net_servico (192.168.100.0/26)
Gateway: `192.168.100.1` (r1_hq eth1)

| Device   | IP             | Role                         |
|----------|----------------|------------------------------|
| srv_dns  | 192.168.100.10 | DNS server                   |
| srv_web  | 192.168.100.11 | Web server (HTTP)            |
| srv_db   | 192.168.100.12 | Database — access restricted |

### Branch 1 clients — net_polo1 (192.168.100.64/26)
Gateway: `192.168.100.65` (r2_br1 eth0)

| Device   | IP             |
|----------|----------------|
| pc1_br1  | 192.168.100.66 |
| pc2_br1  | 192.168.100.67 |
| pc3_br1  | 192.168.100.68 |

### Branch 2 clients — net_polo2 (192.168.100.128/26)
Gateway: `192.168.100.129` (r3_br2 eth0)

| Device   | IP              |
|----------|-----------------|
| pc1_br2  | 192.168.100.130 |
| pc2_br2  | 192.168.100.131 |
| pc3_br2  | 192.168.100.132 |

### Management — net_gerencia (192.168.100.192/26)
Gateway: `192.168.100.193` (r1_hq eth0)

| Device   | IP              |
|----------|-----------------|
| admin_pc | 192.168.100.194 |

### Internet devices — net_internet (203.0.113.0/24)
Gateway: `203.0.113.1` (r4_edge eth0)

| Device         | IP           | Role                      |
|----------------|--------------|---------------------------|
| srv_public_web | 203.0.113.10 | Public web server         |
| ext_client     | 203.0.113.20 | Simulated external client |

## How to run

```bash
bash scripts/02_hosts/run.sh
bash scripts/02_hosts/test.sh
```

## What the test checks

1. **IP presence** — verifies every device has its expected IP using `ip addr show`
2. **Kernel routing tables** — prints `ip route` for each host to confirm the
   connected route was auto-created and show that no default gateway exists yet
