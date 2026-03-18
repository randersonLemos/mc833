# Análise do Protocolo e Desempenho da Aplicação de Streaming

Este documento detalha o funcionamento do protocolo de comunicação implementado, a estrutura dos pacotes e uma análise de desempenho baseada nas especificações do código fornecido.

## 1. Protocolo e Diagrama de Sequência

O sistema utiliza um protocolo customizado sobre UDP para a troca de comandos e um encapsulamento RTP (Real-time Transport Protocol) para o streaming de vídeo.

### Diagrama de Sequência

O diagrama abaixo ilustra a interação entre cliente e servidor para os principais comandos.

```mermaid
sequenceDiagram
    participant Cliente
    participant Servidor

    Note over Cliente, Servidor: Fase de Inicialização
    Cliente->>Servidor: Envia comando (ex: "catalogo")
    Servidor-->>Cliente: Retorna resposta de texto (lista de vídeos)

    Note over Cliente, Servidor: Fase de Streaming
    Cliente->>Servidor: Envia comando "stream <nome_do_video>"
    Servidor-->>Cliente: Retorna confirmação "[STREAM] Iniciando..."
    loop Transmissão do Vídeo
        Servidor-->>Cliente: Envia Pacote RTP [Seq_Num N]
        Servidor-->>Cliente: Envia Pacote RTP [Seq_Num N+1]
        Servidor-->>Cliente: Envia Pacote RTP [...]
    end
    Note over Servidor: Fim do arquivo de vídeo.
```

### Justificativa dos Campos e Protocolos

A escolha da pilha de protocolos (IP -> UDP -> RTP/Custom) foi feita pelas seguintes razões:

*   **UDP (User Datagram Protocol):** Foi escolhido como protocolo de transporte por sua natureza não orientada à conexão e baixa latência. Para streaming de vídeo, a velocidade na entrega é mais crítica do que a garantia de que todos os pacotes chegaram, pois o atraso causado por retransmissões (como no TCP) poderia causar congelamentos no vídeo.
*   **Protocolo Customizado (para comandos):** Para comandos como `catalogo` e `help`, um protocolo simples baseado em texto foi implementado. A simplicidade facilita a depuração e a implementação, sendo suficiente para a troca de mensagens curtas e não frequentes.
*   **RTP (Real-time Transport Protocol):** Para o streaming de vídeo, o RTP foi encapsulado sobre UDP. Ele é o padrão da indústria para transporte de mídia em tempo real e fornece campos essenciais:
    *   **Número de Sequência (`seq_num`):** Permite ao cliente detectar a perda de pacotes e reordená-los caso cheguem fora de ordem, garantindo a integridade da sequência de vídeo. No código, ele é incrementado a cada pacote enviado.
    *   **Timestamp:** Ajuda a sincronizar a reprodução do vídeo no cliente, fornecendo informações temporais sobre quando um frame deve ser exibido.
    *   **SSRC (Synchronization Source):** Identifica unicamente a fonte do stream, útil em cenários com múltiplas fontes.
    *   **Tipo de Payload:** Indica o tipo de mídia sendo transportada (no caso, MPEG-TS, payload type 33).

## 2. Catálogo de Vídeos

O servidor, através do código em `servidor/command/catalog.py`, foi implementado para listar dinamicamente todos os arquivos com a extensão `.ts` que se encontram no diretório `videos/`.

Por exemplo, se o diretório `videos/` contiver os seguintes arquivos:

*   `istockphoto-2170838017-640_adpp_is.ts`
*   `medium.ts`
*   `world.ts`

Ao receber o comando `catalogo` do cliente, o servidor irá ler o diretório e retornará a seguinte lista formatada como resposta:

```
[CATALOGO] Vídeos disponíveis:
  1. istockphoto-2170838017-640_adpp_is.ts
  2. medium.ts
  3. world.ts
```
## 3. Estrutura dos Cabeçalhos

A comunicação entre cliente e servidor é feita através de pacotes brutos, cuja estrutura de cabeçalhos é montada manualmente no código.

A estrutura geral de um pacote enviado pela rede é:

`[ Cabeçalho IP | Cabeçalho UDP | Carga Útil (Payload) ]`

Para o streaming de vídeo, a carga útil é um pacote RTP:

`[ Cabeçalho IP | Cabeçalho UDP | [ Cabeçalho RTP | Dados do Vídeo (MPEG-TS) ] ]`

Abaixo, o detalhamento de cada cabeçalho:

#### Cabeçalho IP (20 Bytes)
*   **Versão/IHL (1 byte):** Versão do IP (4) e tamanho do cabeçalho.
*   **TOS (1 byte):** Tipo de Serviço.
*   **Tamanho Total (2 bytes):** Comprimento total do pacote (cabeçalho + dados).
*   **ID (2 bytes):** Identificação do pacote.
*   **Flags/Offset (2 bytes):** Flags de fragmentação e offset.
*   **TTL (1 byte):** Tempo de Vida do pacote.
*   **Protocolo (1 byte):** Protocolo da camada superior (UDP = 17).
*   **Checksum (2 bytes):** Checksum do cabeçalho IP.
*   **IP Origem (4 bytes):** Endereço IP do remetente.
*   **IP Destino (4 bytes):** Endereço IP do destinatário.

#### Cabeçalho UDP (8 Bytes)
*   **Porta Origem (2 bytes):** Porta do serviço remetente.
*   **Porta Destino (2 bytes):** Porta do serviço destinatário.
*   **Tamanho (2 bytes):** Comprimento do segmento UDP (cabeçalho + dados).
*   **Checksum (2 bytes):** Checksum para verificação de erros.

#### Cabeçalho RTP (12 Bytes) - *Usado apenas para vídeo*
*   **V/P/X/CC (1 byte):** Versão (2), Padding, Extensão, CSRC Count.
*   **M/PT (1 byte):** Marcador e Tipo de Payload (33 para MPEG-TS).
*   **Número de Sequência (2 bytes):** Usado para ordenação dos pacotes.
*   **Timestamp (4 bytes):** Usado para sincronia de tempo na reprodução.
*   **SSRC (4 bytes):** Identificador da fonte de sincronização.

## 4. Quantidade de Bytes para Dados

Analisando o arquivo `servidor/command/stream.py`, a quantidade de bytes reservada exclusivamente para os dados de vídeo (a carga útil do RTP) em cada pacote é de **1316 bytes**.

```python
# Lê 1316 bytes (7 pacotes MPEG-TS)
chunk = video_file.read(1316)
```

Essa escolha é intencional, pois um pacote padrão MPEG-TS (usado em transmissões de TV digital e arquivos `.ts`) tem 188 bytes. Ao agrupar 7 desses pacotes, obtemos `7 * 188 = 1316 bytes`, otimizando o envio sem exceder o MTU (Maximum Transmission Unit) típico da rede.

## 5. Quantidade de Pacotes por Frame

A quantidade de pacotes necessária por frame de vídeo não é fixa, dependendo diretamente da **taxa de bits (bitrate)** e da **taxa de frames por segundo (FPS)** de cada arquivo de vídeo (`.ts`).

Para determinar esses valores para os vídeos disponíveis (`world.ts`, `medium.ts`, etc.), você pode utilizar uma ferramenta de análise de mídia como o `ffprobe` (parte da suíte FFmpeg).

### Como Obter o Bitrate e FPS de um Vídeo

Execute o seguinte comando no seu terminal para cada arquivo de vídeo:

```bash
# Substitua 'video.ts' pelo nome do seu arquivo
ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate,bit_rate -of default=noprint_wrappers=1:nokey=1 video.ts
```

O comando retornará dois valores: o primeiro é o FPS (em formato de fração, como `30/1`) e o segundo é o bitrate em bits por segundo.

### Cálculo de Pacotes por Frame

A fórmula é: `Pacotes por Frame = ArredondarParaCima(Tamanho do Frame em Bytes / 1316)`

Onde: `Tamanho do Frame em Bytes = (Bitrate em bps / 8) / FPS`

A seguir, aplicamos essa fórmula aos vídeos do projeto, usando valores de exemplo. **Você deve substituir os valores de bitrate e FPS pelos valores reais obtidos com o `ffprobe`**.

**Exemplo de Cálculo para `world.ts`**

Vamos supor que, ao rodar o `ffprobe`, descobrimos que o vídeo `world.ts` tem as seguintes propriedades:
*   **FPS:** 30
*   **Bitrate:** 6.000.000 bps (6 Mbps)

1.  **Tamanho do Frame em Bytes:**
    `(6.000.000 bps / 8) / 30 fps = 25.000 bytes/frame`

2.  **Pacotes por Frame:**
    `ceil(25.000 bytes / 1316 bytes/pacote) = ceil(19.00) =` **19 pacotes**

Este cálculo deve ser repetido para os arquivos `medium.ts` e `istockphoto-2170838017-640_adpp_is.ts` com seus respectivos valores de bitrate e FPS.

## 6. Taxa de Transmissão para um Stream a 30fps

A taxa de transmissão da rede (bitrate total) para manter um stream a 30fps depende da resolução do vídeo e inclui o overhead dos cabeçalhos (IP, UDP, RTP).

O overhead por pacote é de `20 (IP) + 8 (UDP) + 12 (RTP) = 40 bytes`.
O tamanho total de um pacote de vídeo é `1316 (dados) + 40 (cabeçalhos) = 1356 bytes`.

Vamos calcular a taxa de rede para dois cenários a 30fps:

**Cenário 1: 720p @ 30fps (Bitrate de vídeo: 3.000 Kbps)**

1.  **Pacotes de dados por segundo:**
    `3.000.000 bps / 8 bits/byte = 375.000 bytes/s`
    `375.000 bytes/s / 1316 bytes/pacote ≈ 285 pacotes/s`

2.  **Taxa de transmissão total na rede:**
    `285 pacotes/s * 1356 bytes/pacote = 386.460 bytes/s`
    `386.460 bytes/s * 8 bits/byte = 3.091.680 bps ≈` **3.09 Mbps**

**Cenário 2: 1080p @ 30fps (Bitrate de vídeo: 4.500 Kbps)**

1.  **Pacotes de dados por segundo:**
    `4.500.000 bps / 8 bits/byte = 562.500 bytes/s`
    `562.500 bytes/s / 1316 bytes/pacote ≈ 427 pacotes/s`

2.  **Taxa de transmissão total na rede:**
    `427 pacotes/s * 1356 bytes/pacote = 579.012 bytes/s`
    `579.012 bytes/s * 8 bits/byte = 4.632.096 bps ≈` **4.63 Mbps**

Portanto, para manter um stream a 30fps, a taxa de transmissão da rede necessária seria de aproximadamente **3.09 Mbps** para qualidade 720p e **4.63 Mbps** para 1080p, considerando o overhead dos protocolos.