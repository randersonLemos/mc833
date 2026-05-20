# MC833 — Lab 4: Corporate Network Configuration

Simulated multi-tier corporate network using Docker containers.
Covers static routing, NAT, and iptables firewall rules.

---

## Network Overview

```
net_servico (192.168.100.0/26)
│
├── srv_dns  .10
├── srv_web  .11
├── srv_db   .12
│
├── r1_hq  eth1:.1 ──── eth0:.193 ──── net_gerencia (192.168.100.192/26)
│                                       └── admin_pc .194
│
├── r2_br1 eth1:.2 ──── eth0:.65  ──── net_polo1 (192.168.100.64/26)
│                                       ├── pc1_br1 .66
│                                       ├── pc2_br1 .67
│                                       └── pc3_br1 .68
│
├── r3_br2 eth1:.3 ──── eth0:.129 ──── net_polo2 (192.168.100.128/26)
│                                       ├── pc1_br2 .130
│                                       ├── pc2_br2 .131
│                                       └── pc3_br2 .132
│
└── r4_edge eth1:.4 ─── eth0:203.0.113.1 ── net_internet (203.0.113.0/24)
                                             ├── srv_public_web .10
                                             └── ext_client     .20
```

### Subnets

The base network `192.168.100.0/24` is split into 4 subnets using a `/26` mask
(`255.255.255.192`). Each block has 64 addresses — 62 usable hosts.
The **first usable IP** of each subnet is reserved as the **default gateway**.

---

**🔴 .AA — net_servico (Backbone)**

The core network. All routers connect here, and the corporate servers live here.

| Address             | Role                                      |
|---------------------|-------------------------------------------|
| 192.168.100.0       | Network ID — cannot be assigned           |
| 192.168.100.1       | Gateway — assigned to `eth1` on all routers |
| 192.168.100.2 – .62 | Usable host range                         |
| 192.168.100.63      | Broadcast                                 |

---

**🟢 .BB — net_polo1 (Branch 1)**

Isolated network for the first remote branch (`pc1_br1`, `pc2_br1`, `pc3_br1`).

| Address               | Role                                        |
|-----------------------|---------------------------------------------|
| 192.168.100.64        | Network ID — cannot be assigned             |
| 192.168.100.65        | Gateway — assigned to `eth0` on `r2_br1`    |
| 192.168.100.66 – .126 | Usable host range                           |
| 192.168.100.127       | Broadcast                                   |

---

**🟡 .CC — net_polo2 (Branch 2)**

Isolated network for the second remote branch (`pc1_br2`, `pc2_br2`, `pc3_br2`).

| Address                | Role                                        |
|------------------------|---------------------------------------------|
| 192.168.100.128        | Network ID — cannot be assigned             |
| 192.168.100.129        | Gateway — assigned to `eth0` on `r3_br2`    |
| 192.168.100.130 – .190 | Usable host range                           |
| 192.168.100.191        | Broadcast                                   |

---

**🟣 .DD — net_gerencia (Management)**

Highly restricted administrative network. Only `admin_pc` lives here.

| Address                | Role                                        |
|------------------------|---------------------------------------------|
| 192.168.100.192        | Network ID — cannot be assigned             |
| 192.168.100.193        | Gateway — assigned to `eth0` on `r1_hq`     |
| 192.168.100.194 – .254 | Usable host range                           |
| 192.168.100.255        | Broadcast                                   |

---

**net_internet (Simulated Public Internet)**

| Address       | Role                              |
|---------------|-----------------------------------|
| 203.0.113.1   | `r4_edge` public-facing interface |
| 203.0.113.10  | `srv_public_web`                  |
| 203.0.113.20  | `ext_client`                      |

---

### Device IPs

| Device         | IP                      | Network        |
|----------------|-------------------------|----------------|
| r1_hq          | 192.168.100.1 / .193    | servico / gerencia |
| r2_br1         | 192.168.100.2 / .65     | servico / polo1 |
| r3_br2         | 192.168.100.3 / .129    | servico / polo2 |
| r4_edge        | 192.168.100.4 / 203.0.113.1 | servico / internet |
| srv_dns        | 192.168.100.10          | net_servico    |
| srv_web        | 192.168.100.11          | net_servico    |
| srv_db         | 192.168.100.12          | net_servico    |
| pc1_br1        | 192.168.100.66          | net_polo1      |
| pc2_br1        | 192.168.100.67          | net_polo1      |
| pc3_br1        | 192.168.100.68          | net_polo1      |
| pc1_br2        | 192.168.100.130         | net_polo2      |
| pc2_br2        | 192.168.100.131         | net_polo2      |
| pc3_br2        | 192.168.100.132         | net_polo2      |
| admin_pc       | 192.168.100.194         | net_gerencia   |
| srv_public_web | 203.0.113.10            | net_internet   |
| ext_client     | 203.0.113.20            | net_internet   |

---

## Prerequisites

- Docker and Docker Compose installed
- User must have permission to run `docker exec`

---

## How to Run

### Full setup (all steps at once)

```bash
docker compose up -d
bash setup.sh
```

### Step by step (recommended for learning)

Run each script in order. After each configuration script, run its test to verify before continuing.

**Step 1 — Assign IPs to routers**
```bash
bash scripts/01_assign_routers.sh
bash scripts/01_test_routers.sh
```
Assigns static IPs to all router interfaces and verifies
reachability between routers on the backbone subnet.

**Step 2 — Assign IPs to hosts**
```bash
bash scripts/02_assign_hosts.sh
bash scripts/02_test_ips.sh
```
Assigns static IPs to all servers, client PCs, and internet devices.

**Step 3 — Configure static routes**
```bash
bash scripts/03_routing.sh
bash scripts/03_test_routing.sh
```
Adds routing entries so traffic can flow across subnets.

**Step 4 — Configure NAT**
```bash
bash scripts/04_nat.sh
bash scripts/04_test_nat.sh
```
Enables MASQUERADE on r4_edge so internal hosts can reach the internet.

**Step 5 — Apply firewall rules**
```bash
bash scripts/05_firewall.sh
bash scripts/05_test_firewall.sh
```
Enforces the security policy: isolates branches, blocks DB/management access,
and prevents the internet from initiating connections inward.

---

## Resetting

To start over from scratch:

```bash
docker compose down
docker compose up -d
bash setup.sh
```

All network configuration lives only in container memory — stopping
the containers wipes everything. No cleanup script needed.

---

## Security Policy Summary

| Source       | Destination  | Result  |
|--------------|--------------|---------|
| Polo 1       | srv_dns      | ALLOW   |
| Polo 2       | srv_web      | ALLOW   |
| Polo 1 / 2   | Internet     | ALLOW (via NAT) |
| Polo 1       | Polo 2       | BLOCK   |
| Polo 2       | Polo 1       | BLOCK   |
| Any Polo     | srv_db       | BLOCK   |
| Any Polo     | net_gerencia | BLOCK   |
| admin_pc     | Any Polo     | BLOCK   |
| Internet     | Internal     | BLOCK (new connections) |
| Internal     | Internet     | ALLOW (replies back in) |
