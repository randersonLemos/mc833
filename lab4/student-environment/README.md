# MC833 — Lab 4: Desafio Corporativo

Simulação de uma arquitetura de rede corporativa completa usando containers Docker.
Cada container age como um roteador, servidor ou PC cliente — sem hardware real.

---

## Visão Geral

Este laboratório cobre:

- Roteamento estático em redes com múltiplos níveis
- NAT (Network Address Translation)
- Regras de firewall com `iptables`
- Segmentação de rede com subnets
- Proteção de recursos sensíveis com isolamento

---

## Requisitos do Desafio

### Conectividade Básica

| Origem     | Destino                        | Deve funcionar? |
|------------|--------------------------------|-----------------|
| Polo 1     | Servidor DNS (`srv_dns`)       | Sim             |
| Polo 2     | Servidor Web (`srv_web`) HTTP  | Sim             |
| Polo 1 e 2 | Internet pública (`203.0.113.10`) via NAT | Sim  |

### Isolamento e Segurança

| Origem            | Destino              | Deve funcionar? |
|-------------------|----------------------|-----------------|
| Polo 1            | Polo 2               | Não — bloqueio bidirecional |
| Polo 2            | Polo 1               | Não — bloqueio bidirecional |
| Qualquer Polo     | Banco de Dados (`srv_db`) | Não        |
| Qualquer Polo     | Gerência (`net_gerencia`) | Não        |
| admin_pc          | Qualquer Polo        | Não             |
| Internet          | Redes internas       | Não — apenas novas conexões bloqueadas |
| Redes internas    | Internet             | Sim — respostas permitidas (stateful) |

### Obrigações de Subnetting

- Utilizar uma rede de **Classe C**
- Utilizar máscara que permita exatamente **4 sub-redes**
- Solução: `192.168.100.0/24` dividida em `/26` → 4 blocos de 64 endereços

---

## Arquitetura da Rede

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

---

## Subnets

Base: `192.168.100.0/24` dividida em 4 subnets com máscara `/26` (`255.255.255.192`).
O **primeiro IP utilizável** de cada subnet é reservado como **gateway padrão**.

---

**.AA — net_servico (Backbone)**

Rede central. Todos os roteadores conectam aqui. Servidores corporativos residem aqui.

| Endereço            | Papel                                       |
|---------------------|---------------------------------------------|
| 192.168.100.0       | Network ID — não pode ser atribuído         |
| 192.168.100.1       | Gateway — atribuído ao `eth1` dos roteadores|
| 192.168.100.2 – .62 | Range utilizável                            |
| 192.168.100.63      | Broadcast                                   |

---

**.BB — net_polo1 (Filial 1)**

Rede isolada da primeira filial (`pc1_br1`, `pc2_br1`, `pc3_br1`).

| Endereço              | Papel                                       |
|-----------------------|---------------------------------------------|
| 192.168.100.64        | Network ID — não pode ser atribuído         |
| 192.168.100.65        | Gateway — atribuído ao `eth0` do `r2_br1`   |
| 192.168.100.66 – .126 | Range utilizável                            |
| 192.168.100.127       | Broadcast                                   |

---

**.CC — net_polo2 (Filial 2)**

Rede isolada da segunda filial (`pc1_br2`, `pc2_br2`, `pc3_br2`).

| Endereço               | Papel                                       |
|------------------------|---------------------------------------------|
| 192.168.100.128        | Network ID — não pode ser atribuído         |
| 192.168.100.129        | Gateway — atribuído ao `eth0` do `r3_br2`   |
| 192.168.100.130 – .190 | Range utilizável                            |
| 192.168.100.191        | Broadcast                                   |

---

**.DD — net_gerencia (Gerência)**

Rede altamente restrita. Apenas `admin_pc` reside aqui.

| Endereço               | Papel                                       |
|------------------------|---------------------------------------------|
| 192.168.100.192        | Network ID — não pode ser atribuído         |
| 192.168.100.193        | Gateway — atribuído ao `eth0` do `r1_hq`    |
| 192.168.100.194 – .254 | Range utilizável                            |
| 192.168.100.255        | Broadcast                                   |

---

**net_internet (Internet pública simulada)**

| Endereço      | Papel                               |
|---------------|-------------------------------------|
| 203.0.113.1   | `r4_edge` — interface pública (NAT) |
| 203.0.113.10  | `srv_public_web`                    |
| 203.0.113.20  | `ext_client` (atacante externo)     |

---

## Tabela de Dispositivos

| Dispositivo    | IP                          | Rede               | Função                    |
|----------------|-----------------------------|--------------------|---------------------------|
| r1_hq          | 192.168.100.1 / .193        | servico / gerencia | Roteador principal        |
| r2_br1         | 192.168.100.2 / .65         | servico / polo1    | Roteador da Filial 1      |
| r3_br2         | 192.168.100.3 / .129        | servico / polo2    | Roteador da Filial 2      |
| r4_edge        | 192.168.100.4 / 203.0.113.1 | servico / internet | Roteador de borda (NAT)   |
| srv_dns        | 192.168.100.10              | net_servico        | Servidor DNS              |
| srv_web        | 192.168.100.11              | net_servico        | Servidor Web (HTTP)       |
| srv_db         | 192.168.100.12              | net_servico        | Banco de Dados (restrito) |
| admin_pc       | 192.168.100.194             | net_gerencia       | PC de Administração       |
| pc1_br1        | 192.168.100.66              | net_polo1          | Cliente Filial 1          |
| pc2_br1        | 192.168.100.67              | net_polo1          | Cliente Filial 1          |
| pc3_br1        | 192.168.100.68              | net_polo1          | Cliente Filial 1          |
| pc1_br2        | 192.168.100.130             | net_polo2          | Cliente Filial 2          |
| pc2_br2        | 192.168.100.131             | net_polo2          | Cliente Filial 2          |
| pc3_br2        | 192.168.100.132             | net_polo2          | Cliente Filial 2          |
| srv_public_web | 203.0.113.10                | net_internet       | Servidor Web público      |
| ext_client     | 203.0.113.20                | net_internet       | Cliente externo           |

---

## Pré-requisitos

- Docker e Docker Compose instalados
- Permissão para executar `docker exec`

---

## Como Executar

### Setup completo (todos os passos de uma vez)

```bash
docker compose up -d
bash setup.sh
```

### Passo a passo (recomendado para aprendizado)

Execute cada script em ordem. Após cada configuração, rode o teste antes de continuar.

**Passo 1 — Atribuir IPs aos roteadores**
```bash
bash scripts/01_routers/run.sh
bash scripts/01_routers/test.sh
```

**Passo 2 — Atribuir IPs aos hosts**
```bash
bash scripts/02_hosts/run.sh
bash scripts/02_hosts/test.sh
```

**Passo 3 — Configurar rotas estáticas**
```bash
bash scripts/03_routing/run.sh
bash scripts/03_routing/test.sh
```

**Passo 4 — Configurar NAT**
```bash
bash scripts/04_nat/run.sh
bash scripts/04_nat/test.sh
```

**Passo 5 — Aplicar regras de firewall**
```bash
bash scripts/05_firewall/run.sh
bash scripts/05_firewall/test.sh
```

---

## Implementação — Scripts, Comandos e Resultados

Esta seção detalha cada script de implementação: o que faz, quais comandos executa, o objetivo de cada um, e qual estado da rede é atingido após sua execução.

---

### scripts/01_routers — Atribuição de IPs aos Roteadores

**Problema que resolve:** Os containers iniciam sem IPs configurados (o Docker atribui endereços `172.x.x.x` aleatórios que ignoramos). Sem IPs estáticos nos roteadores, não há gateway para nenhuma subnet.

**Comandos executados:**

Para cada roteador, o padrão é sempre flush → assign em cada interface:

```bash
# Remove o IP automático do Docker para evitar dois IPs na mesma interface
docker exec r2_br1 ip addr flush dev eth0

# Atribui o IP estático — este endereço se torna o gateway para os clientes de Polo 1
docker exec r2_br1 ip addr add 192.168.100.65/26 dev eth0

# Repete o padrão para a interface do backbone
docker exec r2_br1 ip addr flush dev eth1
docker exec r2_br1 ip addr add 192.168.100.2/26 dev eth1
```

**Tabela completa de atribuições:**

| Roteador | Interface | IP atribuído | Papel |
|---|---|---|---|
| r1_hq | eth0 | 192.168.100.193/26 | Gateway de net_gerencia |
| r1_hq | eth1 | 192.168.100.1/26 | Identidade no backbone |
| r2_br1 | eth0 | 192.168.100.65/26 | Gateway de net_polo1 |
| r2_br1 | eth1 | 192.168.100.2/26 | Identidade no backbone |
| r3_br2 | eth0 | 192.168.100.129/26 | Gateway de net_polo2 |
| r3_br2 | eth1 | 192.168.100.3/26 | Identidade no backbone |
| r4_edge | eth0 | 203.0.113.1/24 | Interface pública (NAT) |
| r4_edge | eth1 | 192.168.100.4/26 | Identidade no backbone |

**Estado da rede após execução:**

- Cada roteador tem dois IPs, um por interface
- O kernel cria automaticamente uma rota conectada para cada subnet atribuída
- Os 4 roteadores conseguem se pingar mutuamente via `net_servico` (mesma subnet, sem roteamento necessário)
- Hosts ainda sem IP — nenhuma conectividade entre subnets ainda

---

### scripts/02_hosts — Atribuição de IPs aos Hosts

**Problema que resolve:** Servidores, PCs clientes, admin e dispositivos de internet não têm identidade de rede. Sem IPs, são invisíveis na rede.

**Comandos executados:**

Cada host segue o mesmo padrão de flush → assign em `eth0`:

```bash
# Remove o IP automático do Docker
docker exec pc1_br1 ip addr flush dev eth0

# Atribui o IP estático dentro da subnet de Polo 1
docker exec pc1_br1 ip addr add 192.168.100.66/26 dev eth0
```

O mesmo padrão se repete para todos os hosts. Exemplos representativos:

```bash
# Servidor DNS — alvo de conectividade de Polo 1
docker exec srv_dns ip addr flush dev eth0
docker exec srv_dns ip addr add 192.168.100.10/26 dev eth0

# Banco de dados — alvo dos bloqueios de firewall
docker exec srv_db ip addr flush dev eth0
docker exec srv_db ip addr add 192.168.100.12/26 dev eth0

# Cliente externo — usado para testar bloqueio da internet
docker exec ext_client ip addr flush dev eth0
docker exec ext_client ip addr add 203.0.113.20/24 dev eth0
```

**Tabela completa de atribuições:**

> **[R]** Roteador — encaminha tráfego entre subnets (ip_forward=1)
> **[S]** Servidor — recurso da rede corporativa
> **[C]** Cliente — usuário final
> **[A]** Administração — acesso restrito
> **[I]** Internet — dispositivo externo simulado

| Tipo | Dispositivo | Interface | IP / Prefixo | Subnet | Gateway do segmento |
|---|---|---|---|---|---|
| **[R]** | r1_hq | eth0 | 192.168.100.193/26 | net_gerencia | — é o gateway |
| **[R]** | r1_hq | eth1 | 192.168.100.1/26 | net_servico | — é o gateway |
| **[R]** | r2_br1 | eth0 | 192.168.100.65/26 | net_polo1 | — é o gateway |
| **[R]** | r2_br1 | eth1 | 192.168.100.2/26 | net_servico | 192.168.100.1 (r1_hq) |
| **[R]** | r3_br2 | eth0 | 192.168.100.129/26 | net_polo2 | — é o gateway |
| **[R]** | r3_br2 | eth1 | 192.168.100.3/26 | net_servico | 192.168.100.1 (r1_hq) |
| **[R]** | r4_edge | eth0 | 203.0.113.1/24 | net_internet | — é o gateway |
| **[R]** | r4_edge | eth1 | 192.168.100.4/26 | net_servico | 192.168.100.1 (r1_hq) |
| **[S]** | srv_dns | eth0 | 192.168.100.10/26 | net_servico | 192.168.100.4 (r4_edge) |
| **[S]** | srv_web | eth0 | 192.168.100.11/26 | net_servico | 192.168.100.4 (r4_edge) |
| **[S]** | srv_db | eth0 | 192.168.100.12/26 | net_servico | 192.168.100.4 (r4_edge) |
| **[C]** | pc1_br1 | eth0 | 192.168.100.66/26 | net_polo1 | 192.168.100.65 (r2_br1) |
| **[C]** | pc2_br1 | eth0 | 192.168.100.67/26 | net_polo1 | 192.168.100.65 (r2_br1) |
| **[C]** | pc3_br1 | eth0 | 192.168.100.68/26 | net_polo1 | 192.168.100.65 (r2_br1) |
| **[C]** | pc1_br2 | eth0 | 192.168.100.130/26 | net_polo2 | 192.168.100.129 (r3_br2) |
| **[C]** | pc2_br2 | eth0 | 192.168.100.131/26 | net_polo2 | 192.168.100.129 (r3_br2) |
| **[C]** | pc3_br2 | eth0 | 192.168.100.132/26 | net_polo2 | 192.168.100.129 (r3_br2) |
| **[A]** | admin_pc | eth0 | 192.168.100.194/26 | net_gerencia | 192.168.100.193 (r1_hq) |
| **[I]** | srv_public_web | eth0 | 203.0.113.10/24 | net_internet | 203.0.113.1 (r4_edge) |
| **[I]** | ext_client | eth0 | 203.0.113.20/24 | net_internet | 203.0.113.1 (r4_edge) |

**Estado da rede após execução:**

- Todos os dispositivos têm IP estático
- O kernel cria uma rota conectada para a própria subnet de cada host. Exemplo em `pc1_br1`:
```
192.168.100.64/26 dev eth0 proto kernel scope link src 192.168.100.66
```
- Hosts da mesma subnet conseguem se pingar diretamente (ex: `pc1_br1` → `pc2_br1`)
- Hosts de subnets diferentes ainda não se alcançam — falta o gateway padrão

---

### scripts/03_routing — Roteamento Estático

**Problema que resolve:** Cada dispositivo conhece apenas sua própria subnet. Um pacote de `pc1_br1` para `srv_dns` é descartado pelo kernel porque não existe rota para `192.168.100.0/26` na tabela de `pc1_br1`.

**Comandos executados — Hosts (gateway padrão):**

```bash
# pc1/2/3_br1 enviam tráfego desconhecido para r2_br1
docker exec pc1_br1 ip route add default via 192.168.100.65
docker exec pc2_br1 ip route add default via 192.168.100.65
docker exec pc3_br1 ip route add default via 192.168.100.65

# pc1/2/3_br2 enviam tráfego desconhecido para r3_br2
docker exec pc1_br2 ip route add default via 192.168.100.129

# admin_pc envia tráfego desconhecido para r1_hq
docker exec admin_pc ip route add default via 192.168.100.193

# Servidores enviam tráfego para a internet via r4_edge
docker exec srv_dns ip route add default via 192.168.100.4

# Dispositivos de internet respondem via r4_edge
docker exec srv_public_web ip route add default via 203.0.113.1
```

**Comandos executados — Roteadores (rotas estáticas):**

```bash
# r1_hq não conhece Polo 1 e Polo 2 diretamente — aprende via backbone
docker exec r1_hq ip route add 192.168.100.64/26  via 192.168.100.2   # → r2_br1
docker exec r1_hq ip route add 192.168.100.128/26 via 192.168.100.3   # → r3_br2
docker exec r1_hq ip route add default             via 192.168.100.4   # → r4_edge

# r2_br1 não conhece Polo 2, gerência ou internet
docker exec r2_br1 ip route add 192.168.100.128/26 via 192.168.100.3  # → r3_br2
docker exec r2_br1 ip route add 192.168.100.192/26 via 192.168.100.1  # → r1_hq
docker exec r2_br1 ip route add default             via 192.168.100.4  # → r4_edge

# r3_br2 não conhece Polo 1, gerência ou internet
docker exec r3_br2 ip route add 192.168.100.64/26  via 192.168.100.2  # → r2_br1
docker exec r3_br2 ip route add 192.168.100.192/26 via 192.168.100.1  # → r1_hq
docker exec r3_br2 ip route add default             via 192.168.100.4  # → r4_edge

# r4_edge precisa das rotas internas para encaminhar respostas do NAT de volta
docker exec r4_edge ip route add 192.168.100.64/26  via 192.168.100.2  # → r2_br1
docker exec r4_edge ip route add 192.168.100.128/26 via 192.168.100.3  # → r3_br2
docker exec r4_edge ip route add 192.168.100.192/26 via 192.168.100.1  # → r1_hq
# r4_edge não precisa de default — a internet já está diretamente em eth0
```

**Estado da rede após execução:**

- Qualquer host consegue alcançar qualquer outro host da rede (sem restrições ainda)
- Tabela de `pc1_br1` após este passo:
```
default via 192.168.100.65 dev eth0
192.168.100.64/26 dev eth0 proto kernel scope link src 192.168.100.66
```
- Caminho de um pacote: `pc1_br1 → r2_br1 → srv_dns` (verificável com `traceroute`)
- Internet ainda inacessível — falta NAT para traduzir os IPs privados

---

### scripts/04_nat — NAT (Network Address Translation)

**Problema que resolve:** Hosts internos têm IPs privados (`192.168.100.x`) que a internet não consegue rotear de volta. Sem NAT, o pacote chega ao destino mas a resposta se perde.

**Comando executado:**

```bash
# Uma única regra no r4_edge resolve o NAT para toda a rede interna
docker exec r4_edge iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
```

**O que cada parte do comando significa:**

| Parte | Significado |
|---|---|
| `-t nat` | Operando na tabela NAT do iptables |
| `-A POSTROUTING` | Aplicado nos pacotes imediatamente antes de sair |
| `-o eth0` | Apenas para pacotes saindo pela interface de internet |
| `-j MASQUERADE` | Reescreve o IP de origem com o IP atual de eth0 (`203.0.113.1`) |

**Fluxo de um pacote com NAT:**

```
pc1_br1 envia:   src=192.168.100.66  dst=203.0.113.10
r4_edge reescreve: src=203.0.113.1   dst=203.0.113.10  → sai pela internet
srv_public_web responde: dst=203.0.113.1
r4_edge restaura: dst=192.168.100.66 → encaminha para r2_br1 → pc1_br1
```

**Estado da rede após execução:**

- Todos os hosts internos conseguem alcançar `srv_public_web` (203.0.113.10)
- O IP que aparece na internet é sempre `203.0.113.1`, independente de qual host originou
- A internet ainda consegue iniciar conexões de volta — isso será bloqueado no próximo passo

---

### scripts/05_firewall — Regras de Firewall

**Problema que resolve:** Toda a rede está aberta. Qualquer host alcança qualquer outro. Os requisitos de isolamento e segurança precisam ser aplicados sem quebrar a conectividade permitida.

**Princípio de ordem:** `ESTABLISHED,RELATED` sempre vem primeiro em cada roteador. Garante que respostas de conexões já abertas não sejam capturadas por uma regra DROP abaixo.

**Comandos executados — r2_br1 (gateway de Polo 1):**

```bash
# Regra 1: permite respostas de conexões que Polo 1 abriu (stateful)
docker exec r2_br1 iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT

# Regra 2: bloqueia Polo 1 de alcançar Polo 2
docker exec r2_br1 iptables -A FORWARD -s 192.168.100.64/26 -d 192.168.100.128/26 -j DROP

# Regra 3: bloqueia Polo 1 de alcançar o banco de dados
docker exec r2_br1 iptables -A FORWARD -s 192.168.100.64/26 -d 192.168.100.12 -j DROP

# Regra 4: bloqueia Polo 1 de alcançar a rede de gerência
docker exec r2_br1 iptables -A FORWARD -s 192.168.100.64/26 -d 192.168.100.192/26 -j DROP
```

**Comandos executados — r3_br2 (gateway de Polo 2):**

```bash
docker exec r3_br2 iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT
docker exec r3_br2 iptables -A FORWARD -s 192.168.100.128/26 -d 192.168.100.64/26  -j DROP
docker exec r3_br2 iptables -A FORWARD -s 192.168.100.128/26 -d 192.168.100.12     -j DROP
docker exec r3_br2 iptables -A FORWARD -s 192.168.100.128/26 -d 192.168.100.192/26 -j DROP
```

**Comandos executados — r1_hq (gateway de gerência):**

```bash
docker exec r1_hq iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT
docker exec r1_hq iptables -A FORWARD -s 192.168.100.192/26 -d 192.168.100.64/26  -j DROP
docker exec r1_hq iptables -A FORWARD -s 192.168.100.192/26 -d 192.168.100.128/26 -j DROP
docker exec r1_hq iptables -A FORWARD -s 192.168.100.192/26 -d 192.168.100.12     -j DROP
```

**Comandos executados — r4_edge (firewall stateful da internet):**

```bash
# Permite respostas de conexões iniciadas internamente (ex: NAT de volta)
docker exec r4_edge iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT

# Bloqueia qualquer nova conexão vinda de eth0 (internet)
docker exec r4_edge iptables -A FORWARD -i eth0 -m state --state NEW -j DROP
```

**Estado da rede após execução:**

| Origem | Destino | Estado final |
|---|---|---|
| pc1_br1 | srv_dns (.10) | Alcança |
| pc1_br2 | srv_web (.11) | Alcança |
| pc*_br1/2 | Internet (203.0.113.10) | Alcança via NAT |
| pc1_br1 | pc1_br2 | Bloqueado (DROP em r2_br1) |
| pc1_br2 | pc1_br1 | Bloqueado (DROP em r3_br2) |
| qualquer polo | srv_db (.12) | Bloqueado (DROP em r2_br1 / r3_br2) |
| qualquer polo | admin_pc (.194) | Bloqueado (DROP em r2_br1 / r3_br2) |
| admin_pc | qualquer polo | Bloqueado (DROP em r1_hq) |
| admin_pc | srv_db (.12) | Bloqueado (DROP em r1_hq) |
| ext_client | qualquer interno | Bloqueado (DROP NEW em r4_edge) |
| interno | ext_client (resposta) | Permitido (ESTABLISHED,RELATED) |

---

## Checklist antes de submeter

- [ ] Os polos não conseguem comunicar entre si
- [ ] Os polos e adm não conseguem acessar o banco de dados
- [ ] Os polos não conseguem comunicar com adm e vice-versa
- [ ] Os polos conseguem se comunicar com a internet
- [ ] A internet não consegue iniciar comunicação com os polos
- [ ] R4 tem rota para a rede interna e NAT configurado

---

## Troubleshooting

**"Sem rota ou bloqueado"** — verifique as rotas:
```bash
docker exec pc2_br1 ip route
docker exec r2_br1 ip route
docker exec r1_hq ip route
```

**"NAT não está funcionando"** — verifique o NAT em R4:
```bash
docker exec r4_edge iptables -t nat -L -v
```

**"Firewall bloqueando o que não deveria"** — verifique as regras:
```bash
docker exec r2_br1 iptables -L FORWARD -v
docker exec r3_br2 iptables -L FORWARD -v
docker exec r1_hq iptables -L FORWARD -v
docker exec r4_edge iptables -L FORWARD -v
```

---

## Reset

Para recomeçar do zero:

```bash
docker compose down
docker compose up -d
bash setup.sh
```

Toda a configuração de rede vive apenas na memória dos containers. Parar os containers apaga tudo — nenhum script de limpeza é necessário.
