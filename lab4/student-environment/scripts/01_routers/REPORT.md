# Atribuição de IPs aos Roteadores

O ponto de partida para a configuração da rede corporativa começa com a atribuição de endereços IP estáticos às interfaces dos quatro roteadores. Os roteadores precisam ser configurados primeiro porque os demais dispositivos dependem dos seus IPs para definir o gateway padrão — sem um gateway configurado, nenhum tráfego consegue cruzar os limites de sub-rede.

---

## Configurações

A rede usa o bloco `192.168.100.0/24` (Classe C) dividido em 4 sub-redes com máscara `/26`, gerando blocos de 64 endereços (62 utilizáveis). O primeiro endereço utilizável de cada sub-rede é reservado como gateway.

| Roteador | Sub-rede | IP atribuído | Papel |
|---|---|---|---|
| r1_hq | net_servico | 192.168.100.1/26 | Identidade no backbone |
| r1_hq | net_gerencia | 192.168.100.193/26 | Gateway da gerência |
| r2_br1 | net_servico | 192.168.100.2/26 | Identidade no backbone |
| r2_br1 | net_polo1 | 192.168.100.65/26 | Gateway da Filial 1 |
| r3_br2 | net_servico | 192.168.100.3/26 | Identidade no backbone |
| r3_br2 | net_polo2 | 192.168.100.129/26 | Gateway da Filial 2 |
| r4_edge | net_servico | 192.168.100.4/26 | Identidade no backbone |
| r4_edge | net_internet | 203.0.113.1/24 | IP público (NAT) |

---

## Implementação

As configurações foram implementadas no script `scripts/01_routers/run.sh`. O script é responsável por identificar quais interfaces de rede estão associadas a cada sub-rede, remover os IPs temporários atribuídos pelo Docker e atribuir os IPs estáticos corretos.

**Problema das interfaces.** Cada roteador possui duas interfaces (`eth0` e `eth1`), uma para cada rede. O Docker não garante qual interface será conectada a qual rede — o mapeamento muda a cada execução. Isso é crítico porque um bridge opera na camada 2: um IP atribuído a uma interface só é alcançável por dispositivos no mesmo bridge físico. Se o IP do gateway da Filial 1 for parado na interface do backbone, os PCs da Filial 1 nunca o encontram. Durante os testes, essa situação foi observada repetidamente — em execuções diferentes, o mesmo roteador teve `eth0` apontando para redes distintas, e aumentar a diferença entre os valores de prioridade do `docker-compose.yml` não resolveu o problema.

**Solução: detecção em tempo de execução.** Quando o Docker inicia um container, atribui automaticamente um IP temporário `172.x.x.x` a cada interface. Esse IP identifica de forma única a qual bridge cada interface está conectada. O script consulta o `docker network inspect` para obter o IP temporário associado a cada rede e, em seguida, localiza qual interface dentro do container possui esse IP. Assim, o nome correto da interface é obtido antes de qualquer configuração, independentemente do que o Docker decidiu nessa execução.

```bash
# Obtém o IP temporário que o Docker atribuiu ao r2_br1 na net_polo1
docker network inspect student-environment_net_polo1 \
    | grep -A4 '"Name": "r2_br1"' \
    | grep -oE '172\.[0-9]+\.[0-9]+\.[0-9]+'

# Localiza qual interface possui esse IP dentro do container
docker exec r2_br1 ip addr show \
    | awk -v ip="172.x.x.x" '
        /^[0-9]+:/ { split($2, a, "@"); iface = a[1]; gsub(/:$/, "", iface) }
        /inet /    { if ($2 ~ ip) print iface }
      '
```

Com a interface correta identificada, os dois comandos abaixo são aplicados para cada rede de cada roteador:

```bash
# Remove o IP temporário do Docker para evitar endereços duplicados na interface
docker exec r2_br1 ip addr flush dev eth1

# Atribui o IP estático à interface correta
docker exec r2_br1 ip addr add 192.168.100.65/26 dev eth1
```

O `ip addr flush` é necessário porque, sem ele, a interface ficaria com dois IPs — o temporário `172.x.x.x` e o estático — gerando rotas conectadas duplicadas na tabela do kernel. O `ip addr add` atribui o endereço estático e, como efeito automático, o kernel cria uma rota conectada para toda a sub-rede naquela interface, por exemplo:

```
192.168.100.64/26 dev eth1 proto kernel scope link src 192.168.100.65
```

Essa rota indica que qualquer pacote destinado à Filial 1 sai diretamente pela interface conectada ao bridge da Filial 1, sem precisar de um roteador intermediário.

---

## Verificação

A verificação foi implementada no script `scripts/01_routers/test.sh` e está dividida em três níveis.

O **Nível 1** confirma que cada IP estático foi atribuído ao container, buscando o endereço na saída do `ip addr show` e reportando em qual interface ele foi parado:

```bash
docker exec r2_br1 ip addr show | grep 192.168.100.65
# Output: inet 192.168.100.65/26 scope global eth1

docker exec r2_br1 ip addr show | grep 192.168.100.2
# Output: inet 192.168.100.2/26 scope global eth0
```

O **Nível 2** verifica se todos os roteadores conseguem se pingar mutuamente pelo backbone `net_servico`. Como todos os IPs do backbone (`.1`, `.2`, `.3`, `.4`) pertencem ao mesmo `/26`, a comunicação deve ocorrer diretamente no bridge, sem roteamento. Este é o teste definitivo: o Nível 1 pode passar mesmo com a interface errada (o IP existe no container), mas o Nível 2 falha se o IP estiver no bridge errado, pois os demais roteadores não o enxergam:

```bash
docker exec r1_hq ping -c1 -W1 192.168.100.2   # r1_hq → r2_br1
docker exec r1_hq ping -c1 -W1 192.168.100.3   # r1_hq → r3_br2
docker exec r1_hq ping -c1 -W1 192.168.100.4   # r1_hq → r4_edge
# ... todos os 12 pares
```

O **Nível 3** exibe a tabela de roteamento de cada roteador para confirmar que o kernel criou as rotas conectadas esperadas após a atribuição dos IPs:

```bash
docker exec r1_hq ip route
docker exec r2_br1 ip route
docker exec r3_br2 ip route
docker exec r4_edge ip route
```

**Resultado:** todos os 20 testes passaram. Os quatro roteadores se comunicam pelo backbone e possuem os IPs corretos nas interfaces corretas.

---

## Tabelas de roteamento após a configuração

As tabelas abaixo mostram o estado do kernel após a execução do script. Neste ponto, cada roteador possui apenas **rotas conectadas** — criadas automaticamente pelo kernel ao receber um IP. Rotas para sub-redes remotas e rota padrão são adicionadas na etapa seguinte (roteamento estático).

Note que os nomes das interfaces (`eth0`/`eth1`) variam conforme o que o Docker atribuiu nessa execução específica.

**r1_hq**
```
192.168.100.0/26   dev eth1  proto kernel  scope link  src 192.168.100.1
192.168.100.192/26 dev eth0  proto kernel  scope link  src 192.168.100.193
```

**r2_br1**
```
192.168.100.0/26   dev eth0  proto kernel  scope link  src 192.168.100.2
192.168.100.64/26  dev eth1  proto kernel  scope link  src 192.168.100.65
```

**r3_br2**
```
192.168.100.0/26   dev eth1  proto kernel  scope link  src 192.168.100.3
192.168.100.128/26 dev eth0  proto kernel  scope link  src 192.168.100.129
```

**r4_edge**
```
192.168.100.0/26   dev eth0  proto kernel  scope link  src 192.168.100.4
203.0.113.0/24     dev eth1  proto kernel  scope link  src 203.0.113.1
```

Cada linha segue o formato `<sub-rede> dev <interface> src <IP-do-roteador>`. A ausência de `via` indica rota direta — o roteador entrega o pacote sem passar por outro salto.
