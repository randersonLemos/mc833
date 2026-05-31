# Regras de Firewall

Com o roteamento e o NAT funcionando, toda a rede está aberta — qualquer host alcança qualquer outro. Este passo aplica a política de segurança: isola as filiais entre si, protege os servidores sensíveis e bloqueia conexões iniciadas pela internet.

---

## Como o iptables FORWARD funciona

As regras são aplicadas na chain **FORWARD**, que processa pacotes que **passam pelo roteador** — não pacotes destinados ao próprio roteador. Quando `pc1_br1` envia um pacote para `srv_db`, ele entra no `r2_br1` pela interface de Polo 1 e sai pela interface do backbone. Esse tráfego passa pela chain FORWARD, onde as regras decidem se ele é entregue ou descartado.

**A ordem das regras importa.** O iptables processa as regras de cima para baixo e para na primeira que casar. Por isso a regra `ESTABLISHED,RELATED → ACCEPT` deve ser sempre a **primeira** em cada roteador. Sem ela, respostas a conexões já abertas seriam capturadas por uma regra DROP abaixo e descartadas — o que quebraria toda conectividade legítima.

---

## Configurações

### r2_br1 — gateway de Polo 1

Todo tráfego saindo de Polo 1 passa por aqui primeiro.

| # | Regra | Ação |
|---|---|---|
| 1 | Qualquer protocolo — estado ESTABLISHED,RELATED | ACCEPT |
| 2 | src=192.168.100.64/26 → dst=192.168.100.128/26 | DROP |
| 3 | src=192.168.100.64/26 → dst=192.168.100.12 | DROP |
| 4 | src=192.168.100.64/26 → dst=192.168.100.192/26 | DROP |
| 5 | src=192.168.100.64/26 → dst=192.168.100.10 | DROP |

### r3_br2 — gateway de Polo 2

Espelho das regras do `r2_br1` com origem `192.168.100.128/26`.

### r1_hq — gateway de gerência

Todo tráfego saindo de `net_gerencia` passa por aqui.

| # | Regra | Ação |
|---|---|---|
| 1 | Qualquer protocolo — estado ESTABLISHED,RELATED | ACCEPT |
| 2 | src=192.168.100.192/26 → dst=192.168.100.64/26 | DROP |
| 3 | src=192.168.100.192/26 → dst=192.168.100.128/26 | DROP |
| 4 | src=192.168.100.192/26 → dst=192.168.100.12 | DROP |
| 5 | src=192.168.100.192/26 → dst=192.168.100.10 | DROP |

### r4_edge — firewall stateful da internet

| # | Regra | Ação |
|---|---|---|
| 1 | Qualquer protocolo — estado ESTABLISHED,RELATED | ACCEPT |
| 2 | entrada pela interface de internet — estado NEW | DROP |

A regra 2 bloqueia qualquer conexão **nova** vinda da internet. Conexões iniciadas internamente continuam funcionando — quando a resposta chega, ela é capturada pela regra 1 (`ESTABLISHED,RELATED`) antes de chegar à regra 2.

---

## Implementação

As regras foram aplicadas com `iptables -A FORWARD` em cada roteador.

**r2_br1 — Polo 1:**
```bash
# Regra 1: permite respostas de conexões já abertas (stateful)
docker exec r2_br1 iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT

# Regra 2: bloqueia Polo 1 → Polo 2
docker exec r2_br1 iptables -A FORWARD -s 192.168.100.64/26 -d 192.168.100.128/26 -j DROP

# Regra 3: bloqueia Polo 1 → srv_db
docker exec r2_br1 iptables -A FORWARD -s 192.168.100.64/26 -d 192.168.100.12 -j DROP

# Regra 4: bloqueia Polo 1 → net_gerencia
docker exec r2_br1 iptables -A FORWARD -s 192.168.100.64/26 -d 192.168.100.192/26 -j DROP

# Regra 5: bloqueia Polo 1 → srv_dns
docker exec r2_br1 iptables -A FORWARD -s 192.168.100.64/26 -d 192.168.100.10 -j DROP
```

**r3_br2 — Polo 2** (espelho com origem `192.168.100.128/26`):
```bash
docker exec r3_br2 iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT
docker exec r3_br2 iptables -A FORWARD -s 192.168.100.128/26 -d 192.168.100.64/26  -j DROP
docker exec r3_br2 iptables -A FORWARD -s 192.168.100.128/26 -d 192.168.100.12     -j DROP
docker exec r3_br2 iptables -A FORWARD -s 192.168.100.128/26 -d 192.168.100.192/26 -j DROP
docker exec r3_br2 iptables -A FORWARD -s 192.168.100.128/26 -d 192.168.100.10     -j DROP
```

**r1_hq — gerência:**
```bash
docker exec r1_hq iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT
docker exec r1_hq iptables -A FORWARD -s 192.168.100.192/26 -d 192.168.100.64/26  -j DROP
docker exec r1_hq iptables -A FORWARD -s 192.168.100.192/26 -d 192.168.100.128/26 -j DROP
docker exec r1_hq iptables -A FORWARD -s 192.168.100.192/26 -d 192.168.100.12     -j DROP
docker exec r1_hq iptables -A FORWARD -s 192.168.100.192/26 -d 192.168.100.10     -j DROP
```

**r4_edge — internet (com detecção de interface):**

A interface de internet do `r4_edge` pode ser `eth0` ou `eth1` dependendo da execução do Docker. O script detecta qual interface possui o IP `203.0.113.x` e usa esse nome na regra — evitando o problema de interface não-determinística:

```bash
# Detecta a interface de internet pelo IP já atribuído no passo 1
R4_INTERNET=$(docker exec r4_edge ip addr show \
    | awk '/^[0-9]+:/ { split($2,a,"@"); iface=a[1]; gsub(/:$/,"",iface) }
           /inet / && $2 ~ /203\.0\.113/ { print iface }')

docker exec r4_edge iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT
docker exec r4_edge iptables -A FORWARD -i "$R4_INTERNET" -m state --state NEW -j DROP
```

---

## Por que srv_dns também é bloqueado

O checklist do trabalho estabelece: *"Os polos e adm não devem conseguir comunicar com DB e DNS"*. A implementação original bloqueava apenas o banco de dados (`srv_db`). O `srv_dns` foi adicionado como regra 5 em `r2_br1`, `r3_br2` e `r1_hq` para satisfazer esse requisito completo.

---

## Verificação

A verificação foi implementada no script `scripts/05_firewall/test.sh` em dois grupos.

**Grupo 1 — deve passar (conectividade permitida):**
```bash
docker exec pc1_br1 ping -c1 -W2 192.168.100.11   # Polo 1 → srv_web
docker exec pc1_br1 ping -c1 -W2 203.0.113.10     # Polo 1 → internet via NAT
docker exec pc1_br2 ping -c1 -W2 192.168.100.11   # Polo 2 → srv_web
docker exec pc1_br2 ping -c1 -W2 203.0.113.10     # Polo 2 → internet via NAT
```

**Grupo 2 — deve bloquear (isolamento):**
```bash
docker exec pc1_br1 ping -c1 -W2 192.168.100.130  # Polo 1 → Polo 2      (DROP em r2_br1)
docker exec pc1_br2 ping -c1 -W2 192.168.100.66   # Polo 2 → Polo 1      (DROP em r3_br2)
docker exec pc1_br1 ping -c1 -W2 192.168.100.12   # Polo 1 → srv_db      (DROP em r2_br1)
docker exec pc1_br2 ping -c1 -W2 192.168.100.12   # Polo 2 → srv_db      (DROP em r3_br2)
docker exec pc1_br1 ping -c1 -W2 192.168.100.10   # Polo 1 → srv_dns     (DROP em r2_br1)
docker exec pc1_br2 ping -c1 -W2 192.168.100.10   # Polo 2 → srv_dns     (DROP em r3_br2)
docker exec pc1_br1 ping -c1 -W2 192.168.100.194  # Polo 1 → admin_pc    (DROP em r2_br1)
docker exec pc1_br2 ping -c1 -W2 192.168.100.194  # Polo 2 → admin_pc    (DROP em r3_br2)
docker exec admin_pc ping -c1 -W2 192.168.100.66  # admin → Polo 1       (DROP em r1_hq)
docker exec admin_pc ping -c1 -W2 192.168.100.130 # admin → Polo 2       (DROP em r1_hq)
docker exec admin_pc ping -c1 -W2 192.168.100.12  # admin → srv_db       (DROP em r1_hq)
docker exec admin_pc ping -c1 -W2 192.168.100.10  # admin → srv_dns      (DROP em r1_hq)
docker exec ext_client ping -c1 -W2 192.168.100.66  # internet → Polo 1  (DROP em r4_edge)
docker exec ext_client ping -c1 -W2 192.168.100.130 # internet → Polo 2  (DROP em r4_edge)
docker exec ext_client ping -c1 -W2 192.168.100.194 # internet → admin   (DROP em r4_edge)
```

Para inspecionar as regras ativas em qualquer momento:
```bash
docker exec r2_br1  iptables -L FORWARD -v
docker exec r3_br2  iptables -L FORWARD -v
docker exec r1_hq   iptables -L FORWARD -v
docker exec r4_edge iptables -L FORWARD -v
```

**Resultado:** todos os 19 testes passaram — `ALL 19 checks PASSED`.
