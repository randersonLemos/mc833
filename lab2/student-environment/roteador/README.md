# Relatório de Desenvolvimento das Atividades
**Instituto de Computação - Universidade Estadual de Campinas**
*Allan M. de Souza, Rafael O. Jarczewski*

---

**Nome:** Randerson Araújo de Lemos
**RA:** 103897

---

### Objetivo do Projeto

Criar um script em Python utilizando a biblioteca Scapy que rode no Roteador. Este script deve:

- Analisar o conteúdo (payload) dos pacotes em tempo real.
- Identificar o ataque através de um padrão de assinatura (uma string ou comando específico que o malfeitor envia).
- Impedir o ataque ou alertar o administrador sem bloquear o IP ou a porta, pois estes são dinâmicos e mudariam em segundos.

---

### Módulos e Funções Principais

#### Módulos Python Customizados:
- **`roteador.py`**: Script principal que inicializa o sniffer e orquestra o fluxo de pacotes.
- **`forward/`**: Módulos responsáveis pelo encaminhamento dos pacotes.
  - `world2server.py`: Encaminha o tráfego do cliente para o servidor.
  - `server2world.py`: Encaminha o tráfego do servidor para o cliente.
- **`package/`**:
  - `content.py`: Formata e exibe os detalhes dos pacotes de forma legível.
- **`firewall/`**: Módulos que implementam as regras de segurança.
  - `layer_network.py`: Filtros de camada 3, baseados em regras de topologia de rede (subnets, tráfego lateral) em vez de IPs estáticos.
  - `layer_transport.py`: Filtros de camada 4 (TCP/UDP).
  - `layer_application.py`: Filtros de camada 7 (conteúdo/payload).
  - `rate_limiter.py`: Controle de frequência para mitigar ataques de força bruta.

#### Funções e Camadas da Biblioteca Scapy:
- **`sniff()`**: Função principal para capturar o tráfego de rede.
- **`sendp()`**: Envia pacotes na camada 2 (enlace), permitindo o controle da interface de saída.
- **`get_if_hwaddr()`**: Obtém o endereço MAC de uma interface de rede.
- **`getmacbyip()`**: Resolve o endereço MAC de um IP na rede local.
- **Camadas**:
  - `Ether()`: Para acessar e manipular o cabeçalho Ethernet (endereços MAC).
  - `IP()`: Para acessar e manipular o cabeçalho IP (endereços IP, TTL).
  - `TCP()`: Para acessar e manipular o cabeçalho TCP (portas, flags, sequence number).
  - `UDP()`: Para acessar e manipular o cabeçalho UDP (portas).
  - `Raw()`: Para acessar o payload (conteúdo) do pacote.

---

## Análise Estatística do Tráfego (Sniffer)

O sniffer foi construído como um roteador virtual em Python, utilizando a biblioteca Scapy para operar em tempo real. A arquitetura foi projetada para ser modular e eficiente, garantindo que a análise de pacotes tenha o mínimo impacto na latência da rede.

A função central do sistema é a `sniff()` do Scapy, configurada para operar de forma contínua e assíncrona. Para evitar a perda de pacotes em cenários de alta vazão, a abordagem adotada foi a seguinte:
1.  **Processamento Leve no Callback**: A função `sniff()` é chamada com o argumento `prn=roteamento`, que designa a função `roteamento()` como o *callback* a ser executado para cada pacote capturado.
2.  **Estrutura de Loop Eficiente**: O parâmetro `store=0` na função `sniff()` é crucial, pois instrui o Scapy a não manter nenhum pacote na memória, liberando recursos imediatamente após o processamento no callback.

### Fluxo de Processamento do Roteador (`roteamento` function)

A função `roteamento(pkt)` é o cérebro do sistema e segue um fluxo de decisão estrito para cada pacote:

1.  **Pré-filtragem**: O pacote é imediatamente descartado se não for um pacote IP ou se for um pacote que o próprio roteador acabou de enviar (verificando os MACs de origem), evitando loops de encaminhamento.
2.  **Aprendizado de MAC (ARP Cache Dinâmico)**: O endereço MAC de origem do pacote é armazenado em um dicionário (`arp_cache`) com o IP de origem como chave. Isso permite que o roteador aprenda dinamicamente os endereços MAC dos clientes na rede, evitando a necessidade de múltiplas consultas ARP para o mesmo host.
3.  **Execução da Cadeia de Firewall**: O pacote é submetido a uma série de verificações de segurança, em ordem:
    - `layer_network.filter_packet(pkt)`: Verifica regras de topologia (ex: impede comunicação lateral entre clientes).
    - `layer_transport.filter_packet(pkt)`: Analisa flags TCP para detectar scans de rede (NULL, FIN, XMAS).
    - `layer_application.filter_packet(pkt)`: Inspeciona o payload em busca de assinaturas de ataque conhecidas.
    - `rate_limiter.filter_packet(pkt)`: Verifica a frequência de pacotes SYN para bloquear ataques de força bruta.
    - Se **qualquer uma** dessas funções retornar `False`, o processamento é interrompido e o pacote é descartado.
4.  **Correção de Checksum**: Antes do encaminhamento, os checksums dos cabeçalhos IP e TCP/UDP são deletados (`del pkt[IP].chksum`). Isso força o Scapy a recalcular os checksums corretamente, um passo vital pois a modificação dos endereços MAC no próximo passo invalidaria os checksums originais.
5.  **Decisão de Roteamento**:
    - **Pacote para o Servidor**: Se o IP de destino é o do servidor (`10.0.1.2`), o pacote é passado para a função `world2server.forward()`. Esta função reescreve o frame Ethernet, definindo o MAC de origem como o do roteador (lado do servidor) e o MAC de destino como o do servidor. O pacote é então enviado pela interface correta (`ETH_SERVER`) usando `sendp()`.
    - **Pacote para o Cliente**: Se o IP de origem é o do servidor, o roteador consulta seu `arp_cache` para encontrar o MAC do cliente de destino. Se não encontrar, ele tenta uma resolução ARP com `getmacbyip()`. Com o MAC em mãos, ele chama `server2world.forward()`, que reescreve o frame Ethernet e o envia pela interface do cliente (`ETH_CLIENT`).
    - **Outros Pacotes**: Qualquer outro tráfego que passe pelos filtros (geralmente pacotes de broadcast/multicast da rede) é simplesmente logado e descartado.

Essa estrutura garante que o roteador virtual seja rápido, seguro e eficiente, tomando decisões de encaminhamento e segurança em tempo real.

### Filtros e Captura

**Filtros BPF (Berkeley Packet Filter) utilizados:**
```
net 10.0.0.0/16
```

**Justificativa:** Por que esses filtros foram escolhidos para a análise?

---

## Detecção de Anomalias e Processamento de Firewall

Nesta etapa, o sniffer atua como um elemento de rede (roteador/firewall) que decide o destino do pacote com base no seu comportamento.

### 2.1 Comparativo Visual: Fluxo Normal vs. Anômalo

Apresenta a comparação lado a lado de como as métricas se comportam quando um ataque é injetado.

### 2.2 Método de Detecção Implementado

**Descreva a lógica utilizada para identificar o tráfego inválido.**

**Critério de Decisão:** Você não pode utilizar IP ou Porta de destino e origem para isso.

**Fluxo de Execução:**
1. O pacote é capturado pela camada de processamento.
2. O método verifica os atributos em relação à lista negra ou limiares (thresholds).
3. **Encaminhamento:** Se normal, o pacote segue para `send()`.
4. **Drop:** Se anômalo, a função retorna um log de alerta e descarta o pacote (não executa o `send()`).

### 2.3 Eficácia do Firewall

**Resultado:** O método foi capaz de mitigar a anomalia?

**Conclusão:** Discorra sobre como o processamento no "roteador virtual" impactou a latência da rede e a segurança do host final.
