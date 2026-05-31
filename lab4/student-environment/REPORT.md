# Relatório Final — Lab 4: Desafio Corporativo

**Disciplina:** MC833 — Laboratório de Redes  
**Aluno:** Randerson Lemos

---

## Objetivo

Configurar uma rede corporativa simulada em containers Docker com múltiplas filiais, roteamento estático, NAT e isolamento por firewall, atendendo aos requisitos de conectividade e segurança do desafio.

---

## Arquitetura

A rede usa o bloco `192.168.100.0/24` (Classe C) dividido em 4 sub-redes com máscara `/26`, gerando exatamente 4 blocos de 64 endereços (62 utilizáveis cada).

```
net_servico (192.168.100.0/26) — backbone corporativo
│
├── srv_dns  192.168.100.10
├── srv_web  192.168.100.11
├── srv_db   192.168.100.12
│
├── r1_hq  (.1) ──── net_gerencia (192.168.100.192/26)
│                     └── admin_pc .194
│
├── r2_br1 (.2) ──── net_polo1 (192.168.100.64/26)
│                     ├── pc1_br1 .66
│                     ├── pc2_br1 .67
│                     └── pc3_br1 .68
│
├── r3_br2 (.3) ──── net_polo2 (192.168.100.128/26)
│                     ├── pc1_br2 .130
│                     ├── pc2_br2 .131
│                     └── pc3_br2 .132
│
└── r4_edge (.4) ─── net_internet (203.0.113.0/24)
                      ├── srv_public_web .10
                      └── ext_client     .20
```

---

## Implementação

A configuração foi dividida em 5 passos executados em sequência. Cada passo tem seu próprio script de configuração (`run.sh`) e de verificação (`test.sh`).

### Passo 1 — Atribuição de IPs aos Roteadores

Cada roteador possui duas interfaces — uma para o backbone e uma para a sub-rede local. O Docker não garante qual interface (`eth0`/`eth1`) será conectada a qual rede, por isso o script detecta a interface correta em tempo de execução: consulta o IP temporário `172.x.x.x` que o Docker atribui a cada interface e localiza qual interface possui esse IP dentro do container. Com a interface correta identificada, remove o IP temporário e atribui o estático.

```bash
# Detecção da interface correta
docker network inspect student-environment_net_polo1 \
    | grep -A4 '"Name": "r2_br1"' \
    | grep -oE '172\.[0-9]+\.[0-9]+\.[0-9]+'

# Atribuição do IP
docker exec r2_br1 ip addr flush dev <interface>
docker exec r2_br1 ip addr add 192.168.100.65/26 dev <interface>
```

**Resultado:** 20/20 testes passaram.

---

### Passo 2 — Atribuição de IPs aos Hosts

Hosts possuem apenas uma interface (`eth0`) — sem o problema de mapeamento não-determinístico dos roteadores. O mesmo padrão flush + assign é aplicado a cada dispositivo.

```bash
docker exec pc1_br1 ip addr flush dev eth0
docker exec pc1_br1 ip addr add 192.168.100.66/26 dev eth0
```

Ao final deste passo, cada host possui apenas a rota conectada para sua sub-rede. Não há rota padrão ainda — dispositivos não conseguem alcançar outras sub-redes.

**Resultado:** 12/12 testes passaram.

---

### Passo 3 — Roteamento Estático

Hosts recebem uma rota padrão apontando para o seu roteador local. Roteadores recebem rotas específicas para as sub-redes que não conhecem diretamente, usando os IPs do backbone como next-hop.

```bash
# Gateway padrão para hosts
docker exec pc1_br1 ip route add default via 192.168.100.65

# Rota estática para roteadores
docker exec r2_br1 ip route add 192.168.100.128/26 via 192.168.100.3
```

O `r4_edge` não recebe rota padrão — é o gateway da internet. Recebe rotas de retorno para todas as sub-redes internas para que as respostas do NAT cheguem ao destino correto.

**Resultado:** 10/10 testes passaram.

---

### Passo 4 — NAT

Uma única regra `iptables MASQUERADE` no `r4_edge` permite que todos os hosts internos acessem a internet com o IP público `203.0.113.1`. A interface de internet é detectada em tempo de execução buscando qual interface do `r4_edge` possui o IP `203.0.113.x`.

```bash
R4_INTERNET=$(docker exec r4_edge ip addr show \
    | awk '/^[0-9]+:/ { split($2,a,"@"); iface=a[1]; gsub(/:$/,"",iface) }
           /inet / && $2 ~ /203\.0\.113/ { print iface }')

docker exec r4_edge iptables -t nat -A POSTROUTING -o "$R4_INTERNET" -j MASQUERADE
```

**Resultado:** 8/8 testes passaram.

---

### Passo 5 — Firewall

Regras `iptables` na chain `FORWARD` de cada roteador implementam a política de segurança. A regra `ESTABLISHED,RELATED → ACCEPT` é sempre a primeira — garante que respostas a conexões já abertas não sejam bloqueadas por uma regra DROP abaixo.

```bash
# Regra 1 — sempre primeira (stateful)
docker exec r2_br1 iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT

# Regras de bloqueio
docker exec r2_br1 iptables -A FORWARD -s 192.168.100.64/26 -d 192.168.100.128/26 -j DROP
docker exec r2_br1 iptables -A FORWARD -s 192.168.100.64/26 -d 192.168.100.12     -j DROP
docker exec r2_br1 iptables -A FORWARD -s 192.168.100.64/26 -d 192.168.100.192/26 -j DROP
docker exec r2_br1 iptables -A FORWARD -s 192.168.100.64/26 -d 192.168.100.10     -j DROP
```

A interface de internet do `r4_edge` também é detectada em tempo de execução para a regra de bloqueio de conexões externas.

**Resultado:** 19/19 testes passaram.

---

## Política de Segurança

| Origem | Destino | Resultado |
|---|---|---|
| Polo 1 | srv_web | Permitido |
| Polo 2 | srv_web | Permitido |
| Polo 1 e 2 | Internet via NAT | Permitido |
| Polo 1 | Polo 2 | Bloqueado (r2_br1) |
| Polo 2 | Polo 1 | Bloqueado (r3_br2) |
| Qualquer Polo | srv_db | Bloqueado (r2_br1 / r3_br2) |
| Qualquer Polo | srv_dns | Bloqueado (r2_br1 / r3_br2) |
| Qualquer Polo | net_gerencia | Bloqueado (r2_br1 / r3_br2) |
| admin_pc | Qualquer Polo | Bloqueado (r1_hq) |
| admin_pc | srv_db | Bloqueado (r1_hq) |
| admin_pc | srv_dns | Bloqueado (r1_hq) |
| Internet | Redes internas | Bloqueado — apenas novas conexões (r4_edge) |

---

## Resultados

| Passo | Descrição | Testes | Resultado |
|---|---|---|---|
| 01 | Atribuição de IPs aos roteadores | 20 | ✓ todos passaram |
| 02 | Atribuição de IPs aos hosts | 12 | ✓ todos passaram |
| 03 | Roteamento estático | 10 | ✓ todos passaram |
| 04 | NAT | 8 | ✓ todos passaram |
| 05 | Firewall | 19 | ✓ todos passaram |
| **Total** | | **69** | **✓ todos passaram** |

---

## Relatórios detalhados

Cada passo possui um relatório detalhado com configurações, comandos, motivações e tabelas de roteamento:

- [`scripts/01_routers/REPORT.md`](scripts/01_routers/REPORT.md)
- [`scripts/02_hosts/REPORT.md`](scripts/02_hosts/REPORT.md)
- [`scripts/03_routing/REPORT.md`](scripts/03_routing/REPORT.md)
- [`scripts/04_nat/REPORT.md`](scripts/04_nat/REPORT.md)
- [`scripts/05_firewall/REPORT.md`](scripts/05_firewall/REPORT.md)
