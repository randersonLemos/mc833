# Step 01 — Router IP Assignment

## Objective

Assign static IP addresses to the four routers so that each one can act as the
**default gateway** for the devices in its local subnet.

Routers are configured before everything else because hosts need a gateway
address before they can be given a default route. Without a gateway, no traffic
can cross subnet boundaries.

---

## Network design

The entire lab uses a single Class C address block: `192.168.100.0/24`.
Divided with a `/26` mask (`255.255.255.192`), this produces exactly 4 subnets
of 64 addresses each (62 usable), satisfying the assignment requirement.

| Subnet | Range | Role |
|---|---|---|
| 192.168.100.0/26 | .1 – .62 | `net_servico` — corporate backbone |
| 192.168.100.64/26 | .65 – .126 | `net_polo1` — Branch 1 clients |
| 192.168.100.128/26 | .129 – .190 | `net_polo2` — Branch 2 clients |
| 192.168.100.192/26 | .193 – .254 | `net_gerencia` — management |

Plus the simulated internet: `203.0.113.0/24`.

All four routers connect to `net_servico` (the backbone). Each also connects to
one local subnet. This shared backbone is what allows routers to use each other
as next-hops without needing complex routing — they are all directly reachable
on the same `/26` segment.

---

## IP assignments

The first usable address of each subnet is reserved for the router gateway.

| Router | Interface → Network | IP assigned | Role |
|---|---|---|---|
| r1_hq | net_servico | 192.168.100.1/26 | backbone identity |
| r1_hq | net_gerencia | 192.168.100.193/26 | gateway for admin_pc |
| r2_br1 | net_servico | 192.168.100.2/26 | backbone identity |
| r2_br1 | net_polo1 | 192.168.100.65/26 | gateway for pc1/2/3_br1 |
| r3_br2 | net_servico | 192.168.100.3/26 | backbone identity |
| r3_br2 | net_polo2 | 192.168.100.129/26 | gateway for pc1/2/3_br2 |
| r4_edge | net_servico | 192.168.100.4/26 | backbone identity |
| r4_edge | net_internet | 203.0.113.1/24 | public-facing IP for NAT |

---

## The interface problem and why detection is needed

Docker connects each router to two networks. Internally, those connections
appear as `eth0` and `eth1`. The `docker-compose.yml` file uses a `priority`
field to suggest which network should become `eth0`, but **Docker does not
reliably respect this field** — the interface assignment is non-deterministic
and changes between runs.

This matters because a **bridge** is a layer-2 device: an IP assigned to an
interface is only reachable by other devices physically connected to the same
bridge. If the polo1 gateway IP lands on the net_servico interface, clients on
the polo1 bridge can never find it.

**The detection strategy:** when a container starts, Docker assigns a temporary
`172.x.x.x` address to each interface. Before our script flushes those
addresses, we can look up which `172.x.x.x` IP Docker assigned to a container
on a specific network (via `docker network inspect`), then find which interface
inside the container currently holds that IP. That tells us the correct
interface name for each network — regardless of whether Docker chose `eth0` or
`eth1`.

---

## Commands executed

### 1. Detect the correct interface for each network

```bash
docker network inspect student-environment_net_polo1 \
    | grep -A4 "\"Name\": \"r2_br1\"" \
    | grep "IPv4Address" \
    | grep -oE '172\.[0-9]+\.[0-9]+\.[0-9]+'
```

**What it does:** queries Docker for the `172.x.x.x` address it assigned to
`r2_br1` on `net_polo1`. This address is only present on the interface that is
physically connected to the polo1 bridge.

```bash
docker exec r2_br1 ip addr show \
    | awk '
        /^[0-9]+:/ { split($2, a, "@"); iface = a[1]; gsub(/:$/, "", iface) }
        /inet /    { if ($2 ~ "172.x.x.x") print iface }
      '
```

**What it does:** scans the interface list inside `r2_br1` and returns the name
of the interface (`eth0` or `eth1`) that currently holds the `172.x.x.x` IP
found in the previous step.

The `split($2, a, "@")` strips the `@if297` suffix that Linux appends to
veth interface names (e.g. `eth1@if297` → `eth1`).

### 2. Flush Docker's auto-assigned IP

```bash
docker exec r2_br1 ip addr flush dev eth1
```

**What it does:** removes all IP addresses from the specified interface.

**Why:** Docker assigns a random `172.x.x.x` address to every interface at
container boot. If we added our static IP without flushing first, the interface
would have two addresses: the Docker one and ours. The Docker address is
meaningless to our network design and would leave stale connected routes in the
kernel routing table.

### 3. Assign the static IP

```bash
docker exec r2_br1 ip addr add 192.168.100.65/26 dev eth1
```

**What it does:** assigns the IP `192.168.100.65` with subnet mask `/26` to
interface `eth1` of container `r2_br1`.

**What happens automatically:** the kernel immediately creates a **connected
route** for the entire subnet:

```
192.168.100.64/26 dev eth1 proto kernel scope link src 192.168.100.65
```

This route means "to reach any address in 192.168.100.64/26, send directly
out eth1 without going through a router." This is what makes `pc1_br1` able to
reach `r2_br1` on the same bridge without any additional routing configuration.

**Why the /26 mask matters:** the mask tells the kernel which addresses are
local (same subnet) and which require a router. With `/26`, the kernel knows
that `.65` through `.126` are directly reachable on this interface.

---

## Final state after execution

Each router has two IP addresses — one per interface:

```
r1_hq:   192.168.100.1/26   (net_servico)    192.168.100.193/26  (net_gerencia)
r2_br1:  192.168.100.2/26   (net_servico)    192.168.100.65/26   (net_polo1)
r3_br2:  192.168.100.3/26   (net_servico)    192.168.100.129/26  (net_polo2)
r4_edge: 192.168.100.4/26   (net_servico)    203.0.113.1/24      (net_internet)
```

Each router's kernel has two connected routes — one per interface. Example for
`r2_br1`:

```
192.168.100.0/26  dev eth0  proto kernel  src 192.168.100.2   ← net_servico
192.168.100.64/26 dev eth1  proto kernel  src 192.168.100.65  ← net_polo1
```

The interface names (`eth0`/`eth1`) will vary between runs — this is the
non-determinism described above. The IPs and subnets are always the same.

---

## Test verification (`test.sh`)

The test has three levels, each building on the previous one.

### Level 1 — IP presence

```bash
docker exec r2_br1 ip addr show | grep 192.168.100.65
docker exec r2_br1 ip addr show | grep 192.168.100.2
```

**What it checks:** that each static IP was successfully assigned to the
container. Also reports which interface it landed on (informational).

**What a PASS means:** the `ip addr add` commands in `run.sh` succeeded and
the address is visible in the kernel.

**What a FAIL means:** the IP was never assigned, likely because the flush or
add command failed.

### Level 2 — Backbone reachability

```bash
docker exec r1_hq ping -c1 -W1 192.168.100.2   # r1_hq → r2_br1
docker exec r2_br1 ping -c1 -W1 192.168.100.3  # r2_br1 → r3_br2
# ... all 12 pairs
```

**What it checks:** that every router can ping every other router on the
`net_servico` backbone — without any static routing configuration.

**Why this works without routing:** all four backbone IPs (`.1`, `.2`, `.3`,
`.4`) are in the same `/26` subnet. Devices on the same subnet communicate
directly at layer 2 through the bridge, with no router needed.

**What a PASS means:** the IP is on the correct bridge. ARP resolved and ICMP
packets were delivered.

**What a FAIL means:** the IP is on the wrong bridge. This is the symptom of
the interface problem — the address is assigned to the container but to an
interface that is physically connected to a different Docker bridge, so other
routers on `net_servico` cannot see it.

This is the most important level: Level 1 can pass even when the interface is
wrong (it only checks that the IP exists, not which bridge it is on). Level 2
is the definitive correctness check.

### Level 3 — Kernel routing tables

```bash
docker exec r2_br1 ip route
```

**What it checks:** displays the routing table of each router to confirm the
kernel created the expected connected routes after IP assignment.

**What to look for:** two entries per router — one for each subnet it is
directly connected to. No `default` route yet (that is configured in step 3).

Example expected output for `r2_br1`:
```
192.168.100.0/26  dev eth0  proto kernel  scope link  src 192.168.100.2
192.168.100.64/26 dev eth1  proto kernel  scope link  src 192.168.100.65
```

The interface names may be `eth0`/`eth1` in any combination depending on what
Docker assigned in this run.
