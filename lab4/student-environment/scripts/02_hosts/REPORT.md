# Atribuição de IPs aos Hosts

Com os roteadores configurados, o segundo passo é atribuir endereços IP estáticos a todos os dispositivos finais da rede: servidores corporativos, PCs clientes das filiais, estação de administração e dispositivos da internet simulada. Sem um IP, um dispositivo é invisível na rede e não pode enviar nem receber tráfego.

---

## Configurações

Diferente dos roteadores, os hosts possuem apenas uma interface (`eth0`) e recebem um único IP dentro da sua sub-rede. O gateway de cada host é o IP do roteador responsável por aquela sub-rede, configurado no passo anterior.

| Dispositivo | IP atribuído | Sub-rede | Gateway |
|---|---|---|---|
| srv_dns | 192.168.100.10/26 | net_servico | 192.168.100.1 (r1_hq) |
| srv_web | 192.168.100.11/26 | net_servico | 192.168.100.1 (r1_hq) |
| srv_db | 192.168.100.12/26 | net_servico | 192.168.100.1 (r1_hq) |
| pc1_br1 | 192.168.100.66/26 | net_polo1 | 192.168.100.65 (r2_br1) |
| pc2_br1 | 192.168.100.67/26 | net_polo1 | 192.168.100.65 (r2_br1) |
| pc3_br1 | 192.168.100.68/26 | net_polo1 | 192.168.100.65 (r2_br1) |
| pc1_br2 | 192.168.100.130/26 | net_polo2 | 192.168.100.129 (r3_br2) |
| pc2_br2 | 192.168.100.131/26 | net_polo2 | 192.168.100.129 (r3_br2) |
| pc3_br2 | 192.168.100.132/26 | net_polo2 | 192.168.100.129 (r3_br2) |
| admin_pc | 192.168.100.194/26 | net_gerencia | 192.168.100.193 (r1_hq) |
| srv_public_web | 203.0.113.10/24 | net_internet | 203.0.113.1 (r4_edge) |
| ext_client | 203.0.113.20/24 | net_internet | 203.0.113.1 (r4_edge) |

---

## Implementação

As configurações foram implementadas no script `scripts/02_hosts/run.sh`. O padrão aplicado a cada host é idêntico ao dos roteadores: remover o IP temporário do Docker e atribuir o IP estático.

```bash
# Remove o IP temporário atribuído pelo Docker
docker exec pc1_br1 ip addr flush dev eth0

# Atribui o IP estático dentro da sub-rede de Polo 1
docker exec pc1_br1 ip addr add 192.168.100.66/26 dev eth0
```

Como hosts têm apenas uma interface (`eth0`), não existe o problema de mapeamento não-determinístico observado nos roteadores. O `eth0` é sempre a única interface de rede do container.

O `ip addr flush` remove o endereço `172.x.x.x` que o Docker atribui automaticamente ao iniciar o container. O `ip addr add` atribui o IP estático com a máscara `/26`, que informa ao kernel quais endereços pertencem à mesma sub-rede. Como efeito automático, o kernel cria uma rota conectada para a sub-rede, por exemplo:

```
192.168.100.64/26 dev eth0 proto kernel scope link src 192.168.100.66
```

Essa rota significa que `pc1_br1` consegue alcançar `pc2_br1` (`.67`) e `pc3_br1` (`.68`) diretamente — mesma sub-rede, mesmo bridge, sem passar pelo roteador. No entanto, nenhum host consegue alcançar dispositivos em outras sub-redes ainda, pois não há rota padrão configurada. Isso é resolvido no próximo passo.

---

## Verificação

A verificação foi implementada no script `scripts/02_hosts/test.sh`. Para cada dispositivo, o teste busca o IP esperado na saída do `ip addr show`:

```bash
docker exec pc1_br1 ip addr show | grep 192.168.100.66
# Output: inet 192.168.100.66/26 scope global eth0
```

Se o IP estiver presente, o teste passa. Em seguida, o script exibe a tabela de roteamento de cada host para confirmar que apenas a rota conectada existe — sem rota padrão, o que é o estado correto ao final deste passo.

**Resultado:** todos os 12 testes passaram — `ALL 12 checks PASSED`.

---

## Tabelas de roteamento após a configuração

Ao final deste passo, cada host possui apenas uma rota — a rota conectada criada automaticamente pelo kernel. Não há rota padrão (`default`) ainda.

**Servidores corporativos (net_servico)**
```
srv_dns  → 192.168.100.0/26  dev eth0  proto kernel  src 192.168.100.10
srv_web  → 192.168.100.0/26  dev eth0  proto kernel  src 192.168.100.11
srv_db   → 192.168.100.0/26  dev eth0  proto kernel  src 192.168.100.12
```

**Clientes da Filial 1 (net_polo1)**
```
pc1_br1  → 192.168.100.64/26  dev eth0  proto kernel  src 192.168.100.66
pc2_br1  → 192.168.100.64/26  dev eth0  proto kernel  src 192.168.100.67
pc3_br1  → 192.168.100.64/26  dev eth0  proto kernel  src 192.168.100.68
```

**Clientes da Filial 2 (net_polo2)**
```
pc1_br2  → 192.168.100.128/26  dev eth0  proto kernel  src 192.168.100.130
pc2_br2  → 192.168.100.128/26  dev eth0  proto kernel  src 192.168.100.131
pc3_br2  → 192.168.100.128/26  dev eth0  proto kernel  src 192.168.100.132
```

**Gerência (net_gerencia)**
```
admin_pc → 192.168.100.192/26  dev eth0  proto kernel  src 192.168.100.194
```

**Internet simulada (net_internet)**
```
srv_public_web → 203.0.113.0/24  dev eth0  proto kernel  src 203.0.113.10
ext_client     → 203.0.113.0/24  dev eth0  proto kernel  src 203.0.113.20
```
