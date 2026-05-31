# Task 05 — Firewall Rules

## What this task does

Applies iptables rules to the FORWARD chain of each router to enforce
the security policy. The FORWARD chain handles packets that **pass through**
a router — not packets destined to the router itself.

Rules applied per router:

| Router   | What it blocks                                            |
|----------|-----------------------------------------------------------|
| r2_br1   | Polo 1 → Polo 2, srv_db, net_gerencia, srv_dns            |
| r3_br2   | Polo 2 → Polo 1, srv_db, net_gerencia, srv_dns            |
| r1_hq    | gerencia → Polo 1, Polo 2, srv_db, srv_dns                |
| r4_edge  | Internet → any internal network (NEW connections only)    |

Every router also has `ESTABLISHED,RELATED → ACCEPT` as its **first rule**
so reply packets from already-open connections are never caught by a DROP below.

## Rule order matters

iptables processes rules top to bottom and stops at the first match.
`ESTABLISHED,RELATED` must always be rule #1 on each router. If it came
after a DROP rule, a response to an open connection could be dropped before
reaching the ACCEPT.

## Why srv_dns is blocked

The assignment checklist explicitly states: *"Os polos e adm não devem
conseguir comunicar com DB e DNS"* — neither the Polo branches nor the
management network may reach the DNS server or the database.

## How to run

```bash
bash scripts/05_firewall/run.sh
bash scripts/05_firewall/test.sh
```

## What the test checks

**Must PASS (allowed connectivity):**
- Polo 1 → srv_web (HTTP server)
- Polo 1 → internet via NAT
- Polo 2 → srv_web (HTTP server)
- Polo 2 → internet via NAT

**Must BLOCK (enforced isolation):**
- Polo 1 ↔ Polo 2 (bidirectional)
- Polo 1 → srv_db
- Polo 2 → srv_db
- Polo 1 → srv_dns
- Polo 2 → srv_dns
- gerencia → Polo 1
- gerencia → Polo 2
- gerencia → srv_db
- gerencia → srv_dns
- Internet → any internal host (NEW connections only; replies still pass)
