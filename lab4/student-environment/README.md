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
