# Roteamento Estático

Após a atribuição de IPs, cada dispositivo conhece apenas a sua própria sub-rede. Um pacote de `pc1_br1` (`.66`) destinado a `srv_web` (`.11`) seria descartado silenciosamente pelo kernel, pois não existe rota para `192.168.100.0/26` na tabela de `pc1_br1`. Este passo ensina cada dispositivo onde encaminhar o tráfego destinado a outras sub-redes.

---

## Configurações

Existem dois tipos de configuração: **gateway padrão** para os hosts e **rotas estáticas** para os roteadores.

**Gateway padrão dos hosts** — cada host envia todo tráfego desconhecido ao roteador da sua sub-rede:

| Dispositivo | Gateway padrão |
|---|---|
| srv_dns, srv_web, srv_db | 192.168.100.4 (r4_edge) |
| pc1/2/3_br1 | 192.168.100.65 (r2_br1) |
| pc1/2/3_br2 | 192.168.100.129 (r3_br2) |
| admin_pc | 192.168.100.193 (r1_hq) |
| srv_public_web, ext_client | 203.0.113.1 (r4_edge) |

**Por que os servidores usam r4_edge e não r1_hq como gateway?**

Os servidores `srv_dns`, `srv_web` e `srv_db` residem em `net_servico` (192.168.100.0/26), que é o próprio backbone. Como todos os quatro roteadores também estão nessa mesma `/26`, os servidores já os alcançam diretamente — sem precisar de gateway para isso.

O gateway padrão só é necessário para tráfego destinado **fora** do `/26`, que na prática significa a internet (`203.0.113.0/24`). Como o `r4_edge` é o gateway da internet e está diretamente alcançável no mesmo backbone, apontá-lo como gateway evita um salto desnecessário:

```
# gateway = r1_hq:   srv_dns → r1_hq → r4_edge → internet   (2 saltos)
# gateway = r4_edge: srv_dns → r4_edge → internet            (1 salto)
```

Usar `r1_hq` funcionaria, mas adicionaria um salto redundante em todo pacote destinado à internet.

**Rotas estáticas dos roteadores** — cada roteador já conhece as sub-redes às quais está diretamente conectado. Precisa aprender apenas as remotas, usando os IPs do backbone como next-hop:

| Roteador | Sub-rede de destino | Next-hop |
|---|---|---|
| r1_hq | 192.168.100.64/26 (Polo 1) | 192.168.100.2 (r2_br1) |
| r1_hq | 192.168.100.128/26 (Polo 2) | 192.168.100.3 (r3_br2) |
| r1_hq | default | 192.168.100.4 (r4_edge) |
| r2_br1 | 192.168.100.128/26 (Polo 2) | 192.168.100.3 (r3_br2) |
| r2_br1 | 192.168.100.192/26 (Gerência) | 192.168.100.1 (r1_hq) |
| r2_br1 | default | 192.168.100.4 (r4_edge) |
| r3_br2 | 192.168.100.64/26 (Polo 1) | 192.168.100.2 (r2_br1) |
| r3_br2 | 192.168.100.192/26 (Gerência) | 192.168.100.1 (r1_hq) |
| r3_br2 | default | 192.168.100.4 (r4_edge) |
| r4_edge | 192.168.100.64/26 (Polo 1) | 192.168.100.2 (r2_br1) |
| r4_edge | 192.168.100.128/26 (Polo 2) | 192.168.100.3 (r3_br2) |
| r4_edge | 192.168.100.192/26 (Gerência) | 192.168.100.1 (r1_hq) |

O `r4_edge` não recebe rota padrão — ele *é* o gateway para a internet. Mas recebe rotas de retorno para todas as sub-redes internas, necessárias para que os pacotes de resposta do NAT cheguem ao host correto.

**Por que r1_hq não aparece na tabela com rota para net_gerencia?**

A tabela de rotas estáticas mostra apenas o que foi **configurado manualmente**. O `r1_hq` não precisa de uma rota estática para `net_gerencia` porque está diretamente conectado a ela — essa rota já existe como rota conectada, criada automaticamente pelo kernel no passo 1:

```
192.168.100.192/26 dev eth0 proto kernel  ← criada automaticamente
```

Todos os roteadores conseguem alcançar a gerência — o caminho de cada um é:

| Roteador | Como alcança net_gerencia |
|---|---|
| r1_hq | Conectado diretamente — entrega o pacote na própria interface |
| r2_br1 | Rota estática → via 192.168.100.1 (r1_hq) |
| r3_br2 | Rota estática → via 192.168.100.1 (r1_hq) |
| r4_edge | Rota estática → via 192.168.100.1 (r1_hq) |

**Por que os roteadores precisam de rotas estáticas?**

Após a atribuição de IPs, cada roteador conhece automaticamente apenas as sub-redes às quais está diretamente conectado. Por exemplo, `r2_br1` conhece `net_servico` e `net_polo1`, mas não tem rota para `net_gerencia`. Se um pacote de `pc1_br1` chegar ao `r2_br1` destinado a `admin_pc` (192.168.100.194), o roteador não encontra rota correspondente e descarta o pacote silenciosamente. As rotas estáticas ensinam cada roteador onde ficam as sub-redes que ele não conhece diretamente.

**Por que os next-hops são sempre IPs do backbone?**

Todos os quatro roteadores compartilham `net_servico` (192.168.100.0/26), o que significa que cada um alcança os demais diretamente — sem intermediários. Por isso os next-hops são sempre IPs do backbone: `r2_br1` não precisa conhecer o caminho completo até `net_gerencia`, apenas sabe que o próximo salto é `r1_hq` (192.168.100.1), que está diretamente acessível na mesma `/26`. O resto é responsabilidade de `r1_hq`.

**Por que o r4_edge não tem rota padrão?**

Os demais roteadores apontam tráfego desconhecido para `r4_edge` porque ele é o gateway da internet. O próprio `r4_edge` já tem a internet na sua interface (`203.0.113.0/24`) — não existe roteador acima dele que conheça mais destinos. Uma rota padrão no `r4_edge` não teria para onde apontar de forma útil.

**Por que o r4_edge precisa das rotas internas?**

O `r4_edge` realiza NAT: quando um host interno acessa a internet, o IP de origem é reescrito para `203.0.113.1`. Quando a resposta chega, o `r4_edge` precisa desfazer a tradução e entregar o pacote de volta ao host original. Para isso, precisa saber como alcançar as sub-redes internas:

```
192.168.100.64/26  via 192.168.100.2  ← pacotes para Polo 1 vão por r2_br1
192.168.100.128/26 via 192.168.100.3  ← pacotes para Polo 2 vão por r3_br2
192.168.100.192/26 via 192.168.100.1  ← pacotes para Gerência vão por r1_hq
```

Sem essas rotas, as respostas da internet chegariam ao `r4_edge` com um IP de destino privado e seriam descartadas, pois ele não saberia para onde encaminhá-las.

---

## Implementação

As configurações foram implementadas no script `scripts/03_routing/run.sh` usando dois comandos:

```bash
# Rota padrão para hosts — todo tráfego desconhecido vai para o roteador local
docker exec pc1_br1 ip route add default via 192.168.100.65

# Rota estática para roteadores — tráfego para Polo 2 vai para r3_br2
docker exec r2_br1 ip route add 192.168.100.128/26 via 192.168.100.3
```

O `ip route add default via <gateway>` instrui o kernel a encaminhar qualquer pacote sem rota específica para o endereço indicado. A partir daí, o roteador local assume a responsabilidade de encontrar o destino.

O `ip route add <sub-rede> via <next-hop>` cria uma rota específica: pacotes destinados àquela sub-rede são encaminhados ao next-hop indicado. O next-hop precisa ser um endereço diretamente alcançável — no caso dos roteadores, todos os next-hops são IPs do backbone `net_servico`, que é uma sub-rede compartilhada por todos eles.

---

## Verificação

A verificação foi implementada no script `scripts/03_routing/test.sh` em três níveis.

O **Nível 1** exibe a tabela de roteamento completa de cada dispositivo com `ip route`, confirmando que a rota padrão e as rotas estáticas foram criadas.

O **Nível 2** testa a conectividade entre sub-redes com `ping`. Neste ponto o firewall ainda não foi aplicado, portanto todos os pings devem passar — inclusive aqueles que serão bloqueados no passo 5 (Polo 1 ↔ Polo 2, Polos → Gerência).

O **Nível 3** executa um `traceroute` de `pc1_br1` até `srv_dns` para confirmar o caminho exato dos pacotes:

```
traceroute to 192.168.100.10, 30 hops max
 1  192.168.100.65   ← r2_br1 (gateway de Polo 1)
 2  192.168.100.10   ← srv_dns (destino)
```

**Resultado:** todos os 10 testes passaram — `ALL 10 checks PASSED`.

---

## Tabelas de roteamento após a configuração

**r1_hq**
```
default                via 192.168.100.4   dev eth1        ← internet via r4_edge
192.168.100.0/26       dev eth1  proto kernel  src .1      ← net_servico (conectada)
192.168.100.64/26      via 192.168.100.2   dev eth1        ← Polo 1 via r2_br1
192.168.100.128/26     via 192.168.100.3   dev eth1        ← Polo 2 via r3_br2
192.168.100.192/26     dev eth0  proto kernel  src .193    ← net_gerencia (conectada)
```

**r2_br1**
```
default                via 192.168.100.4   dev eth0        ← internet via r4_edge
192.168.100.0/26       dev eth0  proto kernel  src .2      ← net_servico (conectada)
192.168.100.64/26      dev eth1  proto kernel  src .65     ← net_polo1 (conectada)
192.168.100.128/26     via 192.168.100.3   dev eth0        ← Polo 2 via r3_br2
192.168.100.192/26     via 192.168.100.1   dev eth0        ← Gerência via r1_hq
```

**r3_br2**
```
default                via 192.168.100.4   dev eth1        ← internet via r4_edge
192.168.100.0/26       dev eth1  proto kernel  src .3      ← net_servico (conectada)
192.168.100.64/26      via 192.168.100.2   dev eth1        ← Polo 1 via r2_br1
192.168.100.128/26     dev eth0  proto kernel  src .129    ← net_polo2 (conectada)
192.168.100.192/26     via 192.168.100.1   dev eth1        ← Gerência via r1_hq
```

**r4_edge**
```
192.168.100.0/26       dev eth0  proto kernel  src .4      ← net_servico (conectada)
192.168.100.64/26      via 192.168.100.2   dev eth0        ← Polo 1 via r2_br1
192.168.100.128/26     via 192.168.100.3   dev eth0        ← Polo 2 via r3_br2
192.168.100.192/26     via 192.168.100.1   dev eth0        ← Gerência via r1_hq
203.0.113.0/24         dev eth1  proto kernel  src .1      ← net_internet (conectada)
```

**Hosts (exemplo representativo por sub-rede)**
```
pc1_br1  → default via 192.168.100.65   |  192.168.100.64/26  dev eth0  src .66
pc1_br2  → default via 192.168.100.129  |  192.168.100.128/26 dev eth0  src .130
admin_pc → default via 192.168.100.193  |  192.168.100.192/26 dev eth0  src .194
srv_dns  → default via 192.168.100.4    |  192.168.100.0/26   dev eth0  src .10
```
