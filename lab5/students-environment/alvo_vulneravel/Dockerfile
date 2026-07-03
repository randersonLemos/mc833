# ---- Estágio de build: só existe para compilar o binário ----
FROM ubuntu:20.04 AS builder
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libc6-dev && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY server.c .
# -fno-stack-protector: desliga stack canary
# -z execstack: permite executar código na pilha (necessário para o shellcode)
RUN gcc -fno-stack-protector -z execstack -o server server.c

# ---- Estágio de runtime: só o necessário para rodar o serviço vulnerável ----
FROM ubuntu:20.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends socat iproute2 gdb netcat python3 python3-pip gcc && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /build/server ./server
RUN echo false > /app/infectado.txt
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# ===== INÍCIO: setup de análise GDB/GEF (bloco removível, ver memória do lab5) =====

# 'curl' pra baixar o GEF, 'file' porque o GEF usa internamente.
RUN apt-get update -qq && apt-get install -y --no-install-recommends curl file && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# GEF atual exige Python 3.10+; esse container tem Python 3.8 (Ubuntu 20.04).
# A tag 2022.06 do GEF é a última compatível com Python 3.6+, sem a sintaxe 'match'.
RUN curl -fsSL https://raw.githubusercontent.com/hugsy/gef/2022.06/gef.py -o /root/.gef-2022.06.py && \
    echo "source /root/.gef-2022.06.py" > /root/.gdbinit

# Locale UTF-8, senão o prompt do GEF (usa caractere ➤) quebra com UnicodeEncodeError.
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Payloads de teste pra análise de buffer overflow em ./server (ver memória do lab5 pra detalhes de cada um).
RUN python3 -c "import sys; sys.stdout.buffer.write(b'AAAABBBBCCCCDDDDEEEE' + b'\x00')" > /app/payload_1_sem_overflow.bin && \
    python3 -c "import sys; sys.stdout.buffer.write(b'X'*49 + b'\x00')" > /app/payload_2_encaixe_exato.bin && \
    python3 -c "import sys; sys.stdout.buffer.write(b'A'*8 + b'B'*8 + b'C'*8 + b'D'*8 + b'E'*8 + b'F'*8 + b'G'*8 + b'H'*8 + b'I'*8 + b'J'*8 + b'\x00')" > /app/payload_3_overflow.bin

# ===== FIM: setup de análise GDB/GEF =====

EXPOSE 9090
# entrypoint.sh configura rota default e em seguida faz `exec setarch x86_64 -R "$@"`,
# desligando ASLR para o CMD e qualquer processo lançado dentro do container.
ENTRYPOINT ["/entrypoint.sh"]
CMD ["socat", "TCP-LISTEN:9090,reuseaddr,fork", "EXEC:./server"]
